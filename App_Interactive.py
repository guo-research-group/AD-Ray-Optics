import streamlit as st
import numpy as np
from rayoptics.environment import *
from rayoptics.optical import opticalmodel

isdark = False
import plotly.graph_objects as go
from scipy.spatial import *
import numpy as np


from visualize.lens import visualize_lens
from visualize.rays import visualize_rays
import plotly.graph_objects as go
import numpy as np

  
  
def main():
  if 'opm' not in st.session_state or 'sm' not in st.session_state:
        st.session_state.opm = OpticalModel()
        
        st.session_state.sm = st.session_state.opm['seq_model']
  
  opm = st.session_state.opm   
  sm  = st.session_state.sm
  osp = opm['optical_spec']
  
  # define field specs
  osp['pupil'] = PupilSpec(osp, key=['object', 'pupil'], value=12.5)
  osp['fov'] = FieldSpec(osp, key=['object', 'angle'], value=20, flds=[0, 0.707, 1], is_relative=True)
  osp['wvls'] = WvlSpec([('F', 0.5), (587.5618, 1.0), ('C', 0.5)], ref_wl=1)
  wv = 587.5618
  # define interface and gap data
  opm.radius_mode = True
  col1, col2 = st.columns(2)
  col1.title("Optical System Parameters")
  lenR = col1.text_input("Lens Radius", value = 12.5)
  n = col1.text_input("Diffraction Index", value = 1.0)
  if col1.button("Add Lens"):
        sm.add_surface([float(lenR), float(n)])

  init_gap = col1.slider("Initial Gap", min_value = 0, max_value = 10, value = 1)
  sm.gaps[0].thi= init_gap
  ray_option = col1.selectbox("Ray Option", ["Paralell", "Point Source"])
  

    
    
  opm.update_model()
  data = visualize_lens(sm, radius = 7)
  if ray_option == "Paralell":
    data.extend(visualize_rays(sm,0,6,wv,x_offsets=np.linspace(-3,3,5), y_offsets=np.linspace(-3,3,5), color = "red"))
  else:
    ray_mult = col1.slider("Ray Multiplier", min_value = 0.0, max_value = 1.0, value = 0.5)
    data.extend(visualize_rays(sm,np.pi * ray_mult,6,wv, color = "red", num_rays = 5))
  figure = go.Figure(data = data)
  figure.update_scenes(aspectmode='data')
  # Update the size of the chart
  figure.update_layout(
      autosize=False,
      width=500,
      height=500,
  )
  col2.plotly_chart(figure)
  if col1.button("Reset"):
    opm = OpticalModel()
    st.session_state.opm = opm 
    st.session_state.sm = opm['seq_model']
    st.rerun()

if __name__ == "__main__":
  main()