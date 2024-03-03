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
  st.title("Lens Visualisation - Simple Interactive")
  if 'lenses' not in st.session_state:
        st.session_state.lenses = []

  opm = OpticalModel()
  sm  = opm['seq_model']
  osp = opm['optical_spec']
  lenses = st.session_state.lenses
  
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
        lens = [float(lenR), float(n)]
        lenses.append(lens)

  for lens in lenses:
      sm.add_surface(lens)

  init_gap = col1.slider("Initial Gap", min_value = 0, max_value = 10, value = 1)
  sm.gaps[0].thi= init_gap  
  opm.update_model()
  data = visualize_lens(sm, radius = 7)
  data.extend(visualize_rays(sm,0,6,wv,x_offsets=np.linspace(-3,3,5), y_offsets=np.linspace(-5,1,5), color = "red"))
  figure = go.Figure(data = data)
  figure.update_scenes(aspectmode='data')
  # Update the size of the chart
  figure.update_layout(
      autosize=False,
      width=500,
      height=500,
  )
  col2.plotly_chart(figure)
  

if __name__ == "__main__":
  main()