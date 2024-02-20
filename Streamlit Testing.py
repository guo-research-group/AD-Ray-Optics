
import streamlit as st
import numpy as np
from rayoptics.environment import *
from rayoptics.optical import opticalmodel

import jax
from jax.numpy import sqrt, copysign, sin
jax.config.update("jax_enable_x64", True)

isdark = False
import plotly.graph_objects as go
from scipy.spatial import *
import numpy as np


from visualize.lens import visualize_lens
from visualize.rays import visualize_rays
import plotly.graph_objects as go
import numpy as np
# create a new optical model and set up aliases
def main():
  st.title("Lens Visualisation")
  opm = OpticalModel()
  sm  = opm['seq_model']
  osp = opm['optical_spec']
  pm = opm['parax_model']
  em = opm['ele_model']
  pt = opm['part_tree']
  ar = opm['analysis_results']

  # define field specs
  osp['pupil'] = PupilSpec(osp, key=['object', 'pupil'], value=12.5)
  osp['fov'] = FieldSpec(osp, key=['object', 'angle'], value=20, flds=[0, 0.707, 1], is_relative=True)
  osp['wvls'] = WvlSpec([('F', 0.5), (587.5618, 1.0), ('C', 0.5)], ref_wl=1)
  wv = 587.5618

  # define interface and gap data
  opm.radius_mode = True
  def_code ="""
sm.gaps[0].thi= 15

# add the surfaces
sm.add_surface([23.713, 4.831, 'N-LAK9', 'Schott'])
sm.add_surface([7331.288, 5.86])
sm.add_surface([-24.456, .975, 'N-SF5,Schott'])
sm.add_surface([21.896, 4.822])
sm.add_surface([86.759, 3.127, 'N-LAK9', 'Schott'])
sm.add_surface([-20.4942, 41.2365])


# update the model
opm.update_model()
data = visualize_lens(sm, radius = 7)
data.extend(visualize_rays(sm,0,6,wv,x_offsets=np.linspace(-3,3,5), y_offsets=np.linspace(-5,1,5), color = "red"))
figure = go.Figure(data = data)
figure.update_scenes(aspectmode='data')
st.plotly_chart(figure)
"""


  code = st.text_area("Code", value = def_code, height = 200)
  if st.button("Run"):
    exec(code)
  
if __name__ == "__main__":
  main()