"""
This file contains the function visualize_lens, which visualizes a lens system by creating a 3D mesh for each surface in the system.
Date: 01/10/2024
Code Author: Alan Fu
"""
import plotly.graph_objects as go
from scipy.spatial import *
import numpy as np

def visualize_lens(sm, N = 100 , radius = 2):
    """
    This function visualizes a lens system by creating a 3D mesh for each surface in the system.

    Parameters:
    sm (System): The optical system to visualize.
    N (int): The number of points along each axis to use for the mesh. The total number of points is N^2.
    radius (float): The radius of the lens. 

    Returns:
    data (list): A list of plotly Mesh3d objects, one for each surface in the system.

    The function works by iterating over each surface in the system, creating a mesh of points on the surface,
    and then using Delaunay triangulation to create a 3D mesh from these points. The mesh is then added to the
    data list, which is returned at the end of the function.
    """
    sd = radius 
    z_bias = sm.gaps[0].thi # Z coord of Lens
    data = []               # Lens visualisation data
    prev_mesh = [[],[],[]]
    mesh = [[],[],[]]
    volume_mesh = [[],[],[]]
    lens = False
    #Goes through each surface and collects mesh data
    for surf_num in range(1, sm.get_num_surfaces()-1):
      prev_mesh = mesh
      prev_vmesh = volume_mesh
      volume_mesh = [[],[],[]]
      mesh = [[],[],[]]
      surf = sm.ifcs[surf_num]
      sd = np.max([surf.surface_od(),sd])
      #print(np.linspace(-sd,sd,50))
      for xj in np.linspace(-sd, sd, N):
        for yk in np.linspace(-sd,sd, N):
            if ((xj **2 + yk ** 2) > (radius ** 2)):
              continue
            z = surf.profile.sag(xj,yk) + z_bias
            if (z_bias + sm.gaps[surf_num].thi >= z):
              mesh[0].append(xj)
              mesh[1].append(yk)
              mesh[2].append(z)
      for angle in np.linspace(0, np.pi, 360):
        x = radius * np.cos(angle)
        y = radius * np.sin(angle)
        z = surf.profile.sag(x,y) + z_bias
        #print(x,y,np.nan_to_num(z))
        volume_mesh[0].append(x)
        volume_mesh[1].append(y)
        volume_mesh[2].append(z)

      z_bias +=  sm.gaps[surf_num].thi

      #Prepare mesh data for Delaunay
      x = mesh[0]
      y = mesh[1]
      z = mesh[2]

      points = np.vstack([x, y]).T

      # Perform Delaunay triangulation
      tri = Delaunay(points)

      # The indices of the triangles are stored in the `simplices` attribute
      i, j, k = tri.simplices.T

      # Adds mesh to plotly data for plotting
      data.append(go.Mesh3d(x=x, y=z, z=y, i=i, j=j, k=k, color='light blue', opacity=0.5))

      if prev_mesh == [[],[],[]]:
        continue
      if(sm.rndx[surf_num] == [1.0, 1.0, 1.0]):
        lens = True
      if (lens):
        # Create the mesh for the wall
        x = np.concatenate([volume_mesh[0], prev_vmesh[0]])
        y = np.concatenate([volume_mesh[1], prev_vmesh[1]])
        z = np.concatenate([volume_mesh[2], prev_vmesh[2]])

        points = np.vstack([x,np.nan_to_num(z)]).T

        # Perform Delaunay triangulation
        tri = Delaunay(points)

        # The indices of the triangles are stored in the `simplices` attribute
        i, j, k = tri.simplices.T
        data.append(go.Mesh3d(x=x, y=z, z=y, i=i, j=j, k=k, color='light blue', opacity=0.5))
        data.append(go.Mesh3d(x=x, y=z, z=-y, i=i, j=j, k=k, color='light blue', opacity=0.5))
        lens = False
      
    return data