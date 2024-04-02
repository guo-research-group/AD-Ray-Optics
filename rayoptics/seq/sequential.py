#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2018 Michael J. Hayford
""" Manager class for a sequential optical model

.. codeauthor: Michael J. Hayford
"""

import itertools
import logging

from anytree import Node

from rayoptics.elem import surface
from . import gap
from . import medium
from rayoptics.raytr import raytrace as rt
from rayoptics.raytr import trace as trace
from rayoptics.raytr import waveabr
from rayoptics.elem import transform as trns
from opticalglass import glassfactory as gfact
from opticalglass import glasserror as ge
from opticalglass import modelglass as mg
from opticalglass import opticalmedium as om
from rayoptics.oprops import doe


import jax.numpy as np
from jax.numpy import sqrt, copysign, sin
#from math import copysign, sqrt
from rayoptics.util.misc_math import isanumber


class SequentialModel:
    """ Manager class for a sequential optical model

    A sequential optical model is a sequence of surfaces and gaps.

    The sequential model has this structure
    ::

        IfcObj  Ifc1  Ifc2  Ifc3 ... Ifci-1   IfcImg
             \  /  \  /  \  /             \   /
             GObj   G1    G2              Gi-1

    where

        - Ifc is a :class:`~rayoptics.seq.interface.Interface` instance
        - G   is a :class:`~rayoptics.seq.gap.Gap` instance

    There are N interfaces and N-1 gaps. The initial configuration has an
    object and image Surface and an object gap.

    The Interface API supports implementation of an optical action, such as
    refraction, reflection, scatter, diffraction, etc. The Interface may be
    realized as a physical profile separating the adjacent gaps or an idealized
    object, such as a thin lens or 2 point HOE.

    The Gap class maintains a simple separation (z translation) and the medium
    filling the gap. More complex coordinate transformations are handled
    through the Interface API.

    Attributes:
        opt_model: parent optical model
        ifcs: list of :class:`~rayoptics.seq.interface.Interface`
        gaps: list of :class:`~rayoptics.seq.gap.Gap`
        lcl_tfrms: forward transform, interface to interface
        rndx: a list with refractive indices for all **wvls**
        z_dir: -1 if gap follows an odd number of reflections, otherwise +1
        gbl_tfrms: global coordinates of each interface wrt the 1st interface
        stop_surface (int): index of stop interface
        cur_surface (int): insertion index for next interface
    """

    def __init__(self, opt_model, do_init=True, **kwargs):
        self.opt_model = opt_model

        self.ifcs = []
        self.gaps = []
        self.z_dir = []

        self.do_apertures = False #changed

        self.stop_surface = None
        self.cur_surface = None

        # derived attributes
        self.gbl_tfrms = []
        self.lcl_tfrms = []

        # data for a wavelength vs index vs gap data arrays
        self.wvlns = []  # sampling wavelengths in nm
        self.rndx = []  # refractive index vs wv and gap

        if do_init:
            self._initialize_arrays()

    def __json_encode__(self):
        attrs = dict(vars(self))
        del attrs['opt_model']
        del attrs['gbl_tfrms']
        del attrs['lcl_tfrms']
        del attrs['wvlns']
        del attrs['rndx']
        return attrs

    def _initialize_arrays(self):
        """ initialize object and image interfaces and intervening gap """
        # add object interface
        self.ifcs.append(surface.Surface('Obj', interact_mode='dummy'))

        tfrm = np.identity(3), np.array([0., 0., 0.])
        self.gbl_tfrms.append(tfrm)
        self.lcl_tfrms.append(tfrm)

        # add object gap
        self.gaps.append(gap.Gap())
        self.z_dir.append(1)
        self.rndx.append([1.0])

        # interfaces are inserted after cur_surface
        self.cur_surface = 0

        # add image interface
        self.ifcs.append(surface.Surface('Img', interact_mode='dummy'))
        self.gbl_tfrms.append(tfrm)
        self.lcl_tfrms.append(tfrm)

    def reset(self):
        self.__init__(self.opt_model)

    def get_num_surfaces(self):
        return len(self.ifcs)

    def path(self, wl=None, start=None, stop=None, step=1):
        """ returns an iterable path tuple for a range in the sequential model

        Args:
            wl: wavelength in nm for path, defaults to central wavelength
            start: start of range
            stop: first value beyond the end of the range
            step: increment or stride of range

        Returns:
            (**ifcs, gaps, lcl_tfrms, rndx, z_dir**)
        """
        if wl is None:
            wl = self.central_wavelength()

        if step < 0:
            gap_start = start - 1 if start is not None else start
        else:
            gap_start = start

        wl_idx = self.index_for_wavelength(wl)
        try:
            rndx = [n[wl_idx] for n in self.rndx[start:stop:step]]
        except IndexError:
            self.wvlns = self.opt_model['osp']['wvls'].wavelengths
            self.rndx = self.calc_ref_indices_for_spectrum(self.wvlns)
            rndx = [n[wl_idx] for n in self.rndx[start:stop:step]]

        path = itertools.zip_longest(self.ifcs[start:stop:step],
                                     self.gaps[gap_start:stop:step],
                                     self.lcl_tfrms[start:stop:step],
                                     rndx,
                                     self.z_dir[start:stop:step])
        return path

    def reverse_path(self, wl=None, start=None, stop=None, step=-1):
        """ returns an iterable path tuple for a range in the sequential model

        Args:
            wl: wavelength in nm for path, defaults to central wavelength
            start: start of range
            stop: first value beyond the end of the range
            step: increment or stride of range

        Returns:
            (**ifcs, gaps, lcl_tfrms, rndx, z_dir**)
        """
        if wl is None:
            wl = self.central_wavelength()

        if step < 0:
            if start is not None:
                gap_start = start - 1
                rndx_start = start - 1
            else:
                gap_start = start
                rndx_start = -1
        else:
            gap_start = start

        tfrms = self.compute_local_transforms(step=-1)
        wl_idx = self.index_for_wavelength(wl)
        rndx = [n[wl_idx] for n in self.rndx[rndx_start:stop:step]]
        z_dir = [-z_dir for z_dir in self.z_dir[start:stop:step]]
        path = itertools.zip_longest(self.ifcs[start:stop:step],
                                     self.gaps[gap_start:stop:step],
                                     tfrms,
                                     rndx,
                                     z_dir)
        return path

    def calc_ref_indices_for_spectrum(self, wvls):
        """ returns a list with refractive indices for all **wvls**

        Args:
            wvls: list of wavelengths in nm
        """
        indices = []
        for g in self.gaps:
            ri = []
            mat = g.medium
            for w in wvls:
                rndx = mat.rindex(w)
                ri.append(rndx)
            indices.append(ri)

        return indices

    def central_wavelength(self):
        """ returns the central wavelength in nm of the model's ``WvlSpec`` """
        spectral_region = self.opt_model['optical_spec'].spectral_region
        return spectral_region.central_wvl

    def index_for_wavelength(self, wvl):
        """ returns index into rndx array for wavelength `wvl` in nm """
        spectral_region = self.opt_model['optical_spec'].spectral_region
        self.wvlns = spectral_region.wavelengths
        return self.wvlns.index(wvl)

    def central_rndx(self, i):
        """ returns the central refractive index of the model's ``WvlSpec`` """
        spectral_region = self.opt_model['optical_spec'].spectral_region
        central_wvl = spectral_region.reference_wvl
        return self.rndx[i][central_wvl]

    def get_surface_and_gap(self, srf=None):
        if srf is None:
            srf = self.cur_surface
        s = self.ifcs[srf]
        if srf == len(self.gaps):
            g = None
        else:
            g = self.gaps[srf]
        return s, g

    def set_cur_surface(self, s):
        self.cur_surface = s

    def set_stop(self):
        """ sets the stop surface to the current surface """
        self.stop_surface = self.cur_surface
        return self.stop_surface

    def __iadd__(self, node):
        if isinstance(node, gap.Gap):
            self.gaps.append(node)
        else:
            self.ifcs.insert(len(self.ifcs)-1, node)
        return self

    def insert(self, ifc, gap, z_dir=1, prev=False):
        """ insert surf and gap at the cur_gap edge of the sequential model
            graph """
        if self.stop_surface is not None:
            num_ifcs = len(self.ifcs)
            if num_ifcs > 2:
                if self.stop_surface > self.cur_surface and \
                   self.stop_surface < num_ifcs - 2:
                    self.stop_surface += 1
        idx = self.cur_surface = (0 if self.cur_surface is None
                                   else self.cur_surface+1)
        self.ifcs.insert(idx, ifc)
        if gap is not None:
            idx_g = idx-1 if prev else idx
            self.gaps.insert(idx_g, gap)
            z_dir = 1 if z_dir is None else z_dir
            new_z_dir = z_dir*self.z_dir[idx_g-1] if idx > 1 else z_dir
            self.z_dir.insert(idx_g, new_z_dir)
        else:
            gap = self.gaps[idx]

        tfrm = np.identity(3), np.array([0., 0., 0.])
        self.gbl_tfrms.insert(idx, tfrm)
        self.lcl_tfrms.insert(idx, tfrm)

        wvls = self.opt_model.optical_spec.spectral_region.wavelengths
        rindex = [gap.medium.rindex(w) for w in wvls]
        self.rndx.insert(idx, rindex)

        if ifc.interact_mode == 'reflect':
            self.update_reflections(start=idx)

    def remove(self, *args, prev=False):
        """Remove surf and gap at cur_surface or an input index argument.

        To avoid invalid sequence states, both an interface and a gap must be
        removed at the same time. The ``prev`` argument, if True, removes the
        gap preceding the interface. The default behavior is to remove the
        following gap.
        """
        if len(args) == 0:
            idx = self.cur_surface
        else:
            idx = args[0]

        num_ifcs = len(self.ifcs)
        # don't allow object or image interfaces to be removed
        if prev:
            if idx == 0 or idx == 1 or idx == num_ifcs:
                raise IndexError
        else:
            if idx == 0 or idx == -1 or idx == num_ifcs:
                raise IndexError

        if self.ifcs[idx].interact_mode == 'reflect':
            self.update_reflections(start=idx)

        # decrement stop surface as needed
        if self.stop_surface is not None:
            if num_ifcs > 2:
                if self.stop_surface > idx and self.stop_surface > 1:
                    self.stop_surface -= 1

        # remove the associated nodes
        pt = self.opt_model['part_tree']
        pt.trim_node(self.ifcs[idx])

        # interface related attribute lists
        del self.ifcs[idx]
        del self.gbl_tfrms[idx]
        del self.lcl_tfrms[idx]

        # gap node and related attribute lists
        idx = idx-1 if prev else idx
        pt.trim_node(self.gaps[idx])

        del self.gaps[idx]
        del self.z_dir[idx]
        del self.rndx[idx]

    def remove_node(self, e_node):
        part_tree = self.opt_model.part_tree
        ifcs = [n.id for n in part_tree.nodes_with_tag(tag='#ifc',
                                                       root=e_node)]
        for ifc in ifcs:
            idx = self.ifcs.index(ifc)
            if (self.stop_surface is not None and
                idx <= self.stop_surface and
                idx > 1):
                self.stop_surface -= 1
            del self.ifcs[idx]
            del self.gaps[idx]
            del self.z_dir[idx]
            del self.rndx[idx]
            del self.lcl_tfrms[idx]
            del self.gbl_tfrms[idx]

    def add_surface(self, surf_data, diffractive_element = 0, **kwargs):
        """ add a surface where `surf_data` is a list that contains:

        [curvature, thickness, refractive_index, v-number, semi-diameter]

        The `curvature` entry is interpreted as radius if `radius_mode` is **True**

        The `thickness` is the signed thickness

        The `refractive_index, v-number` entry can have several forms:

            - **refractive_index, v-number** (numeric)
            - **refractive_index** only -> constant index model
            - **glass_name, catalog_name** as 1 or 2 strings
            - an instance with a `rindex` attribute
            - **air**, str -> om.Air
            - blank -> defaults to om.Air
            - **'REFL'** -> set interact_mode to 'reflect'

        The `semi-diameter` entry is optional. It may also be entered using the
        `sd` keyword argument.

        diffractive_element is list that contains:

        [ p, surface_idx]

        The 'p' is list of coefficients of phase parameters

        The 'surface_idx' is index of which element diffractive element is being a

        """
        radius_mode = self.opt_model.radius_mode
        mat = None
        if len(surf_data) > 2:
            if not isanumber(surf_data[2]):
                if (isinstance(surf_data[2], str)
                    and
                    surf_data[2].upper() == 'REFL'):
                    mat = self.gaps[self.cur_surface].medium
        s, g, z_dir, rn, tfrm = create_surface_and_gap(surf_data,
                                                       prev_medium=mat,
                                                       radius_mode=radius_mode,
                                                       **kwargs)
        self.insert(s, g, z_dir=z_dir)

        root_node = self.opt_model['part_tree'].root_node
        idx = self.cur_surface
        Node(f'i{idx}', id=s, tag='#ifc', parent=root_node)
        if gap is not None:
            Node(f'g{idx}', id=(g, self.z_dir[idx]), tag='#gap', parent=root_node)

        if diffractive_element:
          p = diffractive_element[0]
          surface_idx = diffractive_element[1]
          self.ifcs[1].phase_element = doe.DiffractiveElement(coefficients=p,phase_fct = doe.radial_phase_fct)


    def sync_to_restore(self, opt_model):
        self.opt_model = opt_model
        if hasattr(self, 'optical_spec'):
            opt_model.optical_spec = self.optical_spec
            delattr(self, 'optical_spec')
        init_z_dir = False
        if not hasattr(self, 'z_dir'):
            self.z_dir = []
            init_z_dir = True
            z_dir_work = 1
        for sg in itertools.zip_longest(self.ifcs, self.gaps):
            ifc, g = sg
            if hasattr(ifc, 'sync_to_restore'):
                ifc.sync_to_restore(opt_model)
            if g:
                if hasattr(g, 'sync_to_restore'):
                    g.sync_to_restore(self)
                if init_z_dir:
                    if ifc.interact_mode == 'reflect':
                        z_dir_work = -z_dir_work
                    self.z_dir.append(z_dir_work)

        self.ifcs[0].interact_mode = 'dummy'
        self.ifcs[-1].interact_mode = 'dummy'

        if not hasattr(self, 'do_apertures'):
            self.do_apertures = True

    def update_model(self, **kwargs):
        # delta n across each surface interface must be set to some
        #  reasonable default value. use the index at the central wavelength
        spectral_region = self.opt_model['optical_spec'].spectral_region
        ref_wl = spectral_region.reference_wvl

        self.wvlns = spectral_region.wavelengths
        self.rndx = self.calc_ref_indices_for_spectrum(self.wvlns)
        n_before = self.rndx[0][ref_wl]

        z_dir_before = self.z_dir[0]

        seq = itertools.zip_longest(self.ifcs, self.gaps)

        for i, sg in enumerate(seq):
            ifc, g = sg
            z_dir_after = copysign(1, z_dir_before)
            if ifc.interact_mode == 'reflect':
                z_dir_after = -z_dir_after

            # leave rndx data unsigned, track change of sign using z_dir
            if g is not None:
                n_after = self.rndx[i][ref_wl]
                #if z_dir_after < 0:
                    #n_after = -n_after
                n_after *= np.sign(z_dir_after) #changed
                ifc.delta_n = n_after - n_before
                n_before = n_after

                z_dir_before = z_dir_after
                self.z_dir[i] = z_dir_after

            # call update() on the surface interface
            ifc.update()

        self.gbl_tfrms = self.compute_global_coords()
        self.lcl_tfrms = self.compute_local_transforms()

    def update_optical_properties(self, **kwargs):
        if self.do_apertures:
            if len(self.ifcs) > 2:
                self.set_clear_apertures()

    def apply_scale_factor(self, scale_factor):
        for i, sg in enumerate(self.path()):
            ifc, g, lcl_tfrm, rndx, z_dir = sg
            ifc.apply_scale_factor(scale_factor)
            if g:
                g.apply_scale_factor(scale_factor)

        self.gbl_tfrms = self.compute_global_coords()
        self.lcl_tfrms = self.compute_local_transforms()

    def flip(self, idx1: int, idx2: int) -> None:
        """Flip interfaces and gaps from *idx1* thru *idx2*."""
        def partial_reverse(list_, idx1: int, idx2: int):
            for i in range(0, int((idx2 - idx1)/2)+1):
                a, b = idx1+i, idx2-i
                if a < b:
                    (list_[a], list_[b]) = (list_[b], list_[a])

        if idx2 < idx1:
            idx1, idx2 = idx2, idx1
        partial_reverse(self.ifcs, idx1, idx2)
        partial_reverse(self.gaps, idx1, idx2-1)

        for ifc in self.ifcs[idx1:idx2+1]:
            ifc.flip()

        if self.stop_surface is not None:
            # if the stop surface is in the flip range, flip it too
            stop_idx = self.stop_surface
            if stop_idx >= idx1 and stop_idx <= idx2:
                self.stop_surface = idx2 - (stop_idx - idx1)

        self.update_model()

    def set_from_specsheet(self, specsheet):
        if 'parax_data' not in self.opt_model['analysis_results']:
            return
        if self.opt_model['analysis_results']['parax_data'] is None:
            return
        if len(specsheet.imager_inputs) == 2:
            fod = self.opt_model['analysis_results']['parax_data'].fod
            f_old = fod.efl
            f_new = specsheet.imager.f
            scale_factor = f_new/f_old
            if scale_factor != 1.0:
                self.apply_scale_factor(scale_factor)

            if specsheet.conjugate_type == 'finite':
                self.gaps[0].thi = scale_factor*fod.pp1 - specsheet.imager.s
                self.gaps[-1].thi = specsheet.imager.sp - scale_factor*fod.ppk
            elif specsheet.conjugate_type == 'infinite':
                self.gaps[-1].thi = specsheet.imager.sp - scale_factor*fod.ppk

    def insert_surface_and_gap(self):
        s = surface.Surface()
        g = gap.Gap()
        self.insert(s, g)
        return s, g

    def update_reflections(self, start):
        """ update interfaces and gaps following insertion of a mirror """

        for i, sg in enumerate(self.path(start=start), start=start):
            ifc, g, lcl_tfrm, rndx, z_dir = sg
            if i > start:
                ifc.apply_scale_factor(-1)
                if g:
                    g.apply_scale_factor(-1)
                    self.z_dir[i] = -z_dir

    def get_rndx_and_imode(self):
        """ get list of signed refractive index and interact mode for sequence. """
        central_wvl = self.opt_model['osp']['wvls'].reference_wvl
        rndx_and_imode = []
        for i in range(len(self.rndx)):
            rndx = self.rndx[i][central_wvl]
            n = rndx if self.z_dir[i] > 0 else -rndx
            imode = self.ifcs[i].interact_mode
            rndx_and_imode += [(n, imode)]
        rndx_and_imode += [(n, imode)]
        return rndx_and_imode

    def surface_label_list(self):
        """ list of surface labels or surface number, if no label """
        labels = []
        for i, s in enumerate(self.ifcs):
            if len(s.label) == 0:
                if i == self.stop_surface:
                    labels.append('Stop')
                else:
                    labels.append(str(i))
            else:
                labels.append(s.label)
        return labels

    def list_model(self, path=None):
        cvr = 'r' if self.opt_model.radius_mode else 'c'
        print("              {}            t        medium     mode   zdr"
              "      sd".format(cvr))
        labels = self.surface_label_list()
        path = self.path() if path is None else path
        for i, sg in enumerate(path):
            ifc, gap, _, _, _ = sg
            s = self.list_surface_and_gap(ifc, gp=gap)
            if gap is not None:
                s.append(self.z_dir[i])
            else:
                s.append(self.z_dir[-1])
            fmt = "{0:>5s}: {1:12.6f} {2:#12.6g} {3:>9s} {4:>10s} {6:2n}"
            if s[4] is not None:  # if the sd is not None...
                fmt += "  {5:#10.5g}"
            print(fmt.format(labels[i], *s))

    def list_model_old(self):
        cvr = 'r' if self.opt_model.radius_mode else 'c'
        print("           {}            t        medium     mode         sd"
              .format(cvr))
        for i, sg in enumerate(self.path()):
            ifc, g, _, _, _ = sg
            s = self.list_surface_and_gap(ifc, gp=g)
            fmt = "{0:2n}: {1:12.6f} {2:#12.6g} {3:>9s} {4.name:>10s}"
            if s[4] is not None:  # if the sd is not None...
                fmt += " {5:#10.5g}"
            print(fmt.format(i, *s))

    def list_gaps(self):
        for i, gp in enumerate(self.gaps):
            print(i, gp)

    def list_surfaces(self):
        for i, s in enumerate(self.ifcs):
            print(i, s)

    def list_surface_and_gap(self, ifc, gp=None):
        """Returns cvr, thi, med, imode, sd for input ifc and gap."""
        cvr = ifc.profile_cv
        if self.opt_model.radius_mode:
            if cvr != 0.0:
                cvr = 1.0/cvr
        sd = ifc.surface_od()
        imode = ifc.interact_mode if ifc.interact_mode == 'reflect' else ""

        if gp is not None:
            thi = gp.thi
            med = gp.medium.name()
        else:
            thi = 0.
            med = ''
        return [cvr, thi, med, imode, sd]

    def list_decenters(self, full=False):
        """List decenter data and gap separations.

        Arguments:
            full: lists all values if True, else only y offset and alpha tilt
        """
        fmt0a = ("              thi    medium/mode          type          x"
                 "          y       alpha      beta       gamma")
        fmt0b = ("              thi    medium/mode          type          y"
                 "       alpha")
        fmt1a = ("{:5n}:                {:>10s}  {:>14s} {:#10.5g} {:#10.5g}"
                 " {:#10.5g} {:#10.5g} {:#10.5g}")
        fmt1b = ("{:5n}:                {:>10s}  {:>14s} {:#10.5g}"
                 " {:#10.5g}")
        fmt1c = "{:5n}:                {:>10s}"
        fmt2 = "{:5n}: {:#12.6g}    {:>9s}"

        # print header
        if full:
            print(fmt0a)
        else:
            print(fmt0b)

        for i, sg in enumerate(self.path()):
            ifc, gap, lcl_tfrm, rndx, z_dir = sg
            imode = (ifc.interact_mode if ifc.interact_mode != 'transmit'
                     else "")

            if ifc.decenter is not None:
                d = ifc.decenter
                if full:
                    print(fmt1a.format(i, imode, d.dtype,
                                       d.dec[0], d.dec[1],
                                       d.euler[0], d.euler[1], d.euler[2]))
                else:
                    print(fmt1b.format(i, imode, d.dtype,
                                       d.dec[1], d.euler[0]))
            elif gap is None:  # final interface, just list interact_mode
                print(fmt1c.format(i, imode))

            if gap:
                print(fmt2.format(i, gap.thi, gap.medium.name()))

    def list_sg(self):
        """List decenter data and gap separations. """
        cvrd = 'r' if self.opt_model.radius_mode else 'c'
        fmt0a = ("               {}               mode              type"
                 "          y       alpha")
        fmt0b = ("                       t           medium")
        fmt1 = ("{:>5s}: {:#12.6g}       {:>10s}     {:>14s} {:#10.5g}"
                " {:#10.5g}")
        fmt2 = ("{:>5s}: {:#12.6g}       {:>10s}")
        fmt3 = ("                {:#12.6g}    {:>9s}")

        # print header
        print(fmt0a.format(cvrd))
        print(fmt0b)

        labels = self.surface_label_list()
        for i, sg in enumerate(self.path()):
            ifc, gap, lcl_tfrm, rndx, z_dir = sg
            s = self.list_surface_and_gap(ifc, gap)
            s.append(z_dir)
            cvr, thi, med, imode, sd, z_dir = s
            if ifc.decenter is not None:
                d = ifc.decenter
                print(fmt1.format(labels[i], cvr, imode, d.dtype,
                                  d.dec[1], d.euler[0]))
            else:
                print(fmt2.format(labels[i], cvr, imode))

            if gap:
                print(fmt3.format(gap.thi, gap.medium.name()))

    def list_elements(self):
        for i, gp in enumerate(self.gaps):
            if gp.medium.name().lower() != 'air':
                print(self.ifcs[i].profile,
                      self.ifcs[i+1].profile,
                      gp)

    def listobj_str(self):
        o_str = ""
        stop_idx = self.stop_surface
        for i, sg in enumerate(self.path()):
            ifc, gap, lcl_tfrm, rndx, z_dir = sg
            if stop_idx is not None and i == stop_idx:
                o_str += f'{i} (stop): ' + ifc.listobj_str()
            else:
                o_str += f'{i}: ' + ifc.listobj_str()
            if gap is not None:
                gap_str = gap.listobj_str()
                semicolon_indx = gap_str.find(';')
                o_str += (gap_str[:semicolon_indx] +
                          f" ({int(z_dir):+})" +
                          gap_str[semicolon_indx:] + '\n')

        o_str += f'\ndo apertures: {self.do_apertures}'
        return o_str

    def trace_fan(self, fct, fi, xy, num_rays=21, **kwargs):
        """ xy determines whether x (=0) or y (=1) fan """
        osp = self.opt_model.optical_spec
        fld = osp.field_of_view.fields[fi]
        wvl = self.central_wavelength()
        foc = osp.defocus.get_focus()

        rs_pkg, cr_pkg = trace.setup_pupil_coords(self.opt_model,
                                                  fld, wvl, foc)
        fld.chief_ray = cr_pkg
        fld.ref_sphere = rs_pkg

        # Use the central wavelength reference image point for the wavefront error calculations
        ref_img_pt = rs_pkg[0]

        wvls = osp.spectral_region
        fans_x = []
        fans_y = []
        fan_start = np.array([0., 0.])
        fan_stop = np.array([0., 0.])
        fan_start[xy] = -1.0
        fan_stop[xy] = 1.0
        fan_def = [fan_start, fan_stop, num_rays]
        max_rho_val = 0.0
        max_y_val = 0.0
        rc = []
        for wi, wvl in enumerate(wvls.wavelengths):
            rc.append(wvls.render_colors[wi])

            rs_pkg, cr_pkg = trace.setup_pupil_coords(self.opt_model,
                                                      fld, wvl, foc,
                                                      image_pt=ref_img_pt)
            fld.chief_ray = cr_pkg
            fld.ref_sphere = rs_pkg
            fan = trace.trace_fan(self.opt_model, fan_def, fld, wvl, foc,
                                  img_filter=lambda p, ray_pkg:
                                  fct(p, xy, ray_pkg, fld, wvl, foc), **kwargs)
            f_x = []
            f_y = []
            for p, y_val in fan:
                f_x.append(p[xy])
                f_y.append(y_val)
                if abs(p[xy]) > max_rho_val:
                    max_rho_val = abs(p[xy])
                if abs(y_val) > max_y_val:
                    max_y_val = abs(y_val)
            fans_x.append(f_x)
            fans_y.append(f_y)
        fans_x = np.array(fans_x)
        fans_y = np.array(fans_y)
        return fans_x, fans_y, (max_rho_val, max_y_val), rc

    def trace_grid(self, fct, fi, wl=None, num_rays=21, form='grid',
                   append_if_none=True, **kwargs):
        """ fct is applied to the raw grid and returned as a grid  """
        osp = self.opt_model.optical_spec
        wvls = osp.spectral_region
        wvl = self.central_wavelength()
        wv_list = wvls.wavelengths if wl is None else [wvl]
        fld = osp.field_of_view.fields[fi]
        foc = osp.defocus.get_focus()

        rs_pkg, cr_pkg = trace.setup_pupil_coords(self.opt_model,
                                                  fld, wvl, foc)
        fld.chief_ray = cr_pkg
        fld.ref_sphere = rs_pkg

        grids = []
        grid_start = np.array([-1., -1.])
        grid_stop = np.array([1., 1.])
        grid_def = [grid_start, grid_stop, num_rays]
        for wi, wvl in enumerate(wv_list):
            grid = trace.trace_grid(self.opt_model, grid_def, fld, wvl, foc,
                                    form=form, append_if_none=append_if_none,
                                    img_filter=lambda p, ray_pkg:
                                    fct(p, wi, ray_pkg, fld, wvl, foc),
                                    **kwargs)
            grids.append(grid)
        rc = wvls.render_colors
        return grids, rc

    def trace_wavefront(self, fld, wvl, foc, num_rays=32):

        def wave(p, ray_pkg, fld, wvl, foc):
            x = p[0]
            y = p[1]
            if ray_pkg is not None:
                fod = self.opt_model['analysis_results']['parax_data'].fod
                opd = waveabr.wave_abr_full_calc(fod, fld, wvl, foc, ray_pkg,
                                                 fld.chief_ray,
                                                 fld.ref_sphere)
                opd = opd/self.opt_model.nm_to_sys_units(wvl)
            else:
                opd = 0.0
            return np.array([x, y, opd])

        rs_pkg, cr_pkg = trace.setup_pupil_coords(self.opt_model,
                                                  fld, wvl, foc)
        fld.chief_ray = cr_pkg
        fld.ref_sphere = rs_pkg

        grid_start = np.array([-1., -1.])
        grid_stop = np.array([1., 1.])
        grid_def = (grid_start, grid_stop, num_rays)

        grid = trace.trace_grid(self.opt_model, grid_def, fld, wvl, foc,
                                img_filter=lambda p, ray_pkg:
                                wave(p, ray_pkg, fld, wvl, foc), form='grid')
        return grid

    # def set_clear_apertures(self):
    #     def rd(v):
    #         """ take 2d length of input vector v """
    #         return np.sqrt(v[0]*v[0]+v[1]*v[1])

    #     if self.get_num_surfaces() > 2:
    #         fields_df = trace.trace_all_fields(self.opt_model)
    #         # a) Select the inc_pt data from the unstacked result and
    #         #    transpose so that intrfcs are the index
    #         inc_pts = fields_df.unstack()['inc_pt'].T
    #         # b) applymap() is used to apply the function rd() to each
    #         #    element in the dataframe
    #         inc_pts_rd = inc_pts.applymap(rd)
    #         # c) apply max() function to each row (i.e. across columns,
    #         #    axis=1)
    #         semi_ap = inc_pts_rd.max(axis=1)
    #         for s, max_ap in zip(self.ifcs[1:-1], semi_ap[1:-1]):
    #             s.set_max_aperture(max_ap)

    def set_clear_apertures_paraxial(self):
        ax_ray, pr_ray, _ = self.opt_model['analysis_results']['parax_data']
        for i, ifc in enumerate(self.ifcs):
            sd = abs(ax_ray[i][0]) + abs(pr_ray[i][0])
            ifc.set_max_aperture(sd)

    def set_clear_apertures(self):
        rayset = trace.trace_boundary_rays(self.opt_model,
                                           use_named_tuples=True)

        for i, s in enumerate(self.ifcs):
            max_ap = -1.0e+10
            update = True
            for f in rayset:
                for p in f:
                    ray = p.ray
                    if len(ray) > i:
                        ap = sqrt(ray[i].p[0]**2 + ray[i].p[1]**2)
                        if ap > max_ap:
                            max_ap = ap
                    else:  # ray failed before this interface, don't update
                        update = False
            if update:
                s.set_max_aperture(max_ap)

    def trace(self, pt0, dir0, wvl, **kwargs):
        return rt.trace(self, pt0, dir0, wvl, **kwargs)

    def compute_global_coords(self, glo=1):
        """ Return global surface coordinates (rot, t) wrt surface glo. """
        tfrms = []
        r, t = np.identity(3), np.array([0., 0., 0.])
        prev = r, t
        tfrms.append(prev)
        if glo > 0:
            # iterate in reverse over the segments before the
            #  global reference surface
            step = -1
            seq = itertools.zip_longest(self.ifcs[glo::step],
                                        self.gaps[glo-1::step])
            ifc, gap = after = next(seq)
            # loop of remaining surfaces in path
            while True:
                try:
                    b4_ifc, b4_gap = before = next(seq)
                    zdist = gap.thi
                    r, t = trns.reverse_transform(ifc, zdist, b4_ifc)
                    t = prev[0].dot(t) + prev[1]
                    r = prev[0].dot(r)
                    prev = r, t
                    tfrms.append(prev)
                    after, ifc, gap = before, b4_ifc, b4_gap
                except StopIteration:
                    break
            tfrms.reverse()

        seq = itertools.zip_longest(self.ifcs[glo:], self.gaps[glo:])
        b4_ifc, b4_gap = before = next(seq)
        prev = np.identity(3), np.array([0., 0., 0.])
        # loop forward over the remaining surfaces in path
        while True:
            try:
                ifc, gap = after = next(seq)
                zdist = b4_gap.thi
                r, t = trns.forward_transform(b4_ifc, zdist, ifc)
                t = prev[0].dot(t) + prev[1]
                r = prev[0].dot(r)
                prev = r, t
                tfrms.append(prev)
                before, b4_ifc, b4_gap = after, ifc, gap
            except StopIteration:
                break

        return tfrms

    def compute_local_transforms(self, seq=None, step=1):
        """ Return forward surface coordinates (r.T, t) for each interface. """
        tfrms = []
        if seq is None:
            seq = itertools.zip_longest(self.ifcs[::step],
                                        self.gaps[::step])
        b4_ifc, b4_gap = before = next(seq)
        while before is not None:
            try:
                ifc, gap = after = next(seq)
            except StopIteration:
                tfrms.append((np.identity(3), np.array([0., 0., 0.])))
                break
            else:
                zdist = step*b4_gap.thi
                r, t = trns.forward_transform(b4_ifc, zdist, ifc)
                rt = r.transpose()
                tfrms.append((rt, t))
                before, b4_ifc, b4_gap = after, ifc, gap

        return tfrms

    def find_matching_ifcs(self):
        rot_tols = dict(atol=1e-14, rtol=1e-8)
        tols = dict(atol=1e-14, rtol=1e-14)
        matches = []
        for i, gi in enumerate(self.gbl_tfrms):
            i1 = i+1
            for j, gj in enumerate(self.gbl_tfrms[i1:], start=i1):
                if (
                        np.allclose(gi[0], gj[0], **rot_tols) and
                        np.allclose(gi[1], gj[1], **tols)
                        ):
                    print(f'coincident surfs: {i} - {j}')
                    matches.append((i, j))
        return matches


def gen_sequence(surf_data_list, **kwargs):
    """ create a sequence iterator from the surf_data_list

    Args:
        surf_data_list: a list of lists containing:
                        [curvature, thickness, refractive_index, v-number]
        **kwargs: keyword arguments

    Returns:
        (**ifcs**, **gaps**, **rndx**, **lcl_tfrms**, **z_dir**)
    """
    ifcs = []
    gaps = []
    rndx = []
    lcl_tfrms = []
    z_dir = []

    for surf_data in surf_data_list:
        s, g, z_dir, rn, tfrm = create_surface_and_gap(surf_data, **kwargs)
        ifcs.append(s)
        gaps.append(g)
        rndx.append(rn)
        lcl_tfrms.append(tfrm)
        z_dir.append(1)
    ifcs[-1].interact_mode = 'dummy'

    n_before = 1.0
    z_dir_before = 1
    for i, s in enumerate(ifcs):
        z_dir_after = copysign(1, z_dir_before)
        n_after = np.copysign(rndx[i], n_before)
        if s.interact_mode == 'reflect':
            n_after = -n_after
            z_dir_after = -z_dir_after

        n_before = n_after
        rndx[i] = n_after
        z_dir_before = z_dir_after
        z_dir[i] = z_dir_after

    seq = itertools.zip_longest(ifcs, gaps[:-2], lcl_tfrms, rndx, z_dir)
    return seq


def create_surface_and_gap(surf_data, radius_mode=False, prev_medium=None,
                           wvl=550.0, **kwargs):
    """ create a surface and gap where `surf_data` is a list that contains:

    [curvature, thickness, refractive_index, v-number, semi-diameter]

    The `curvature` entry is interpreted as radius if `radius_mode` is **True**

    The `thickness` is the signed thickness

    The `refractive_index, v-number` entry can have several forms:

        - **refractive_index, v-number** (numeric)
        - **refractive_index** only -> constant index model
        - **glass_name, catalog_name** as 1 or 2 strings
        - an instance with a `rindex` attribute
        - **air**, str -> om.Air
        - blank -> defaults to om.Air
        - **'REFL'** -> set interact_mode to 'reflect'

    The `semi-diameter` entry is optional. It may also be entered using the
    `sd` keyword argument.
    """
    s = surface.Surface()

    if radius_mode:
        if surf_data[0] != 0.0:
            s.profile.cv = 1.0/surf_data[0]
        else:
            s.profile.cv = 0.0
    else:
        s.profile.cv = surf_data[0]

    z_dir = 1
    sd_indx = None
    num_inputs = len(surf_data)
    if num_inputs > 2:  # look for medium data, possibly followed by sd
        last_k = 3      # assume medium with 1 input
        if num_inputs >= 5:  # 2 input medium plus sd
            last_k = 4
            sd_indx = 4
        elif num_inputs == 4:  # 2 inputs left
            if type(surf_data[2]) == type(surf_data[3]):
                # if same type, assume 2 medium inputs, no sd
                last_k = 4
            else:
                # different types, assume 1 medium input and sd
                last_k = 3
                sd_indx = 3
        try:
            # Feed the right number of inputs into decode_medium
            if last_k == 3:
                mat = medium.decode_medium(surf_data[2])
            else:
                mat = medium.decode_medium(surf_data[2], surf_data[3])
        except ValueError:
            if isinstance(surf_data[2], str):  # string args
                if surf_data[2].upper() == 'REFL':
                    s.interact_mode = 'reflect'
                    mat = prev_medium
                    z_dir = -1

        if sd_indx:
            s.set_max_aperture(surf_data[sd_indx])

    else:  # only curvature and thickness entered, set material to air
        mat = om.Air()

    if kwargs.get('sd', None) is not None:
        s.set_max_aperture(kwargs.get('sd'))
    thi = surf_data[1]
    g = gap.Gap(thi, mat)
    rndx = mat.rindex(wvl)
    tfrm = np.identity(3), np.array([0., 0., thi])

    return s, g, z_dir, rndx, tfrm
