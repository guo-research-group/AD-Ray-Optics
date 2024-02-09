from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import numpy as np
from scipy.spatial import *
from rayoptics.raytr.trace import *


def visualize_rays(sm=None, max_angle=None, radius=10, wv= 400.5618, x_offsets=[0], y_offsets=[0], num_rays= 1, color = 'green'):
    """
    This function visualizes rays in an optical system by creating a 3D scatter plot for each ray.

    Parameters:
    sm (System): The optical system to visualize.
    max_angle (float): The maximum incident angle, in radians.
    radius (float): The radius the valid rays will be within.
    wv (float): The wavelength of the rays.
    x_offsets (list): The x-coordinates of the starting points of the rays.
    y_offsets (list): The y-coordinates of the starting points of the rays.
    num_rays (int): The number of rays to visualize from each starting point. The total number of rays at each starting point is num_rays^2.

    Returns:
    data (list): A list of plotly Scatter3d objects, one for each ray in the system.

    The function works by iterating over each starting point and each angle offset, creating a ray at each combination.
    It then traces the path of each ray through the system, collecting the coordinates of the ray at each point.
    These coordinates are then used to create a 3D scatter plot of the ray, which is added to the data list.
    The function also visualizes the intersection point of each ray with the photosensor, if it is within the bounds of the system.
    """

    if max_angle is not None:
         # Tan Angle Offsets
        angle_offsets = np.linspace(-max_angle, max_angle, num_rays)
    else:
        angle_offsets = [0]

    #Stores Figure data
    data = []

    # Creates each starting coordinate with the y_offset
    idx = 1
    for x_offset in x_offsets:
      for y_offset in y_offsets:
        for ray in angle_offsets: # Creates each tan angle offset
          for ray_angle in angle_offsets:  # Creates each inc angle
                #Sets incident angle and finds ray direction
                if (x_offset ** 2 + y_offset ** 2 > radius ** 2):
                  continue
                inc_angle = ray_angle
                si = np.sin(inc_angle)
                cs = np.cos(inc_angle)
                tn = np.tan(ray)

                st_coord = np.array([x_offset ,y_offset, 0]) # Ray start Co-ord (Add offsets here to alter starting position)

                st_dir = np.array([tn,si,cs]) # Ray starting direction

                output = trace(sm, st_coord, st_dir, wvl=wv) #Traces Ray

                #Collects coordinates of traced ray for visualization
                pt_photosensor = output[0][-1][0]
                if np.abs(pt_photosensor[1]) <= 50:
                    x = []
                    y = []
                    z = []
                    z_bias = 0
                    j = 0
                    for pt in output[0][0::]:
                        y.append(pt[0][1])
                        z.append(pt[0][2]+z_bias)
                        x.append(pt[0][0])
                        if j < len(sm.gaps):
                            z_bias += sm.gaps[j].thi
                            j += 1

                    #Visualizes Ray
                    data.append(go.Scatter3d(x=x, y=z, z=y, mode='lines', line=dict(color=color, width=1), opacity=0.5, name =f"Ray {idx}"))

                    #Visualises intersection point of rays
                    data.append(go.Scatter3d(x=x[::], y= z[::], z=y[::], mode = 'markers', marker=dict(color='black', size=1), showlegend = False))

                    idx += 1
    return data