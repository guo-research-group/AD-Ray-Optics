from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import numpy as np
from scipy.spatial import *
from rayoptics.raytr.trace import *
from multiprocessing import Pool

def trace_ray(args):
    sm, st_coord, st_dir, wv = args
    return trace(sm, st_coord, st_dir, wvl=wv)

def visualize_rays(sm=None, max_angle=None, radius=10, wv= 400.5618, x_offsets=[0], y_offsets=[0], num_rays= 1, color = 'green', visibility = True):
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
        angle_offsets = np.linspace(-max_angle, max_angle, num_rays)
    else:
        angle_offsets = [0]

    data = []
    ouptut = []
    # Create a grid of x_offsets, y_offsets, rays, and ray_angles
    x_offset_grid, y_offset_grid, ray_grid, ray_angle_grid = np.meshgrid(np.array(x_offsets), np.array(y_offsets), np.array(angle_offsets), np.array(angle_offsets))

    # Compute the condition
    condition = x_offset_grid**2 + y_offset_grid**2 <= radius ** 2
    # Apply the condition to the grids
    x_offset_grid = x_offset_grid[condition]
    y_offset_grid = y_offset_grid[condition]
    ray_grid = ray_grid[condition]
    ray_angle_grid = ray_angle_grid[condition]


    # Compute the sin and cos of the incident angles
    si = np.sin(ray_angle_grid)
    cs = np.cos(ray_angle_grid)
    tn = np.tan(ray_grid)


    # Compute the starting coordinates and directions
    st_coord = np.stack([x_offset_grid, y_offset_grid, np.zeros_like(x_offset_grid)], axis=-1)
    st_dir = np.stack([tn, si, cs], axis=-1)

    # Trace the rays
    args = [(sm, coord, dir, wv) for coord, dir in zip(st_coord, st_dir)]
    # Create a pool of workers
    with Pool() as pool:
        output = pool.map(trace_ray, args)

    for out in output:
    #Collects coordinates of traced ray for visualization
      pt_photosensor = out[0][-1][0]
      if np.abs(pt_photosensor[1]) <= 50:
          x = []
          y = []
          z = []
          z_bias = 0
          j = 0
          for pt in out[0][0::]:
              y.append(pt[0][1])
              z.append(pt[0][2]+z_bias)
              x.append(pt[0][0])
              if j < len(sm.gaps):
                  z_bias += sm.gaps[j].thi
                  j += 1
        # Create a Scatter3d object for the rays
          data.append(go.Scatter3d(x=x, y=z, z=y, mode='lines', line=dict(color=color, width=1), opacity=0.5, visible=visibility))

        # Create a Scatter3d object for the intersection points
          data.append(go.Scatter3d(x=x[::], y=z[::], z=y[::], mode='markers', marker=dict(color='black', size=1), showlegend=False))

       


    return data