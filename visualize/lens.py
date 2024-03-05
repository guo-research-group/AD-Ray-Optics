"""
This file contains the function visualize_lens, which visualizes a lens system by creating a 3D mesh for each surface in the system.
Date: 01/10/2024
Code Author: Alan Fu
"""
import plotly.graph_objects as go
from scipy.spatial import *
import numpy as np

def visualize_lens(sm, N = 100 , radius = 2, visibility = True):
    """
    This function visualizes a lens system by creating a 3D mesh for each surface in the system.

    Parameters:
    sm (System): The optical system to visualize.
    N (int): The number of points along each axis to use for the mesh. The total number of points is N^2.
    radius (float): The radius of the lens. 
    visibility (bool): visibility of the lens

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
      # Create an array of angles
      angles = np.linspace(0,np.pi, 50)

      # Create a grid of x and y coordinates
      x, y = np.meshgrid(np.linspace(-sd, sd, N), np.linspace(-sd, sd, N))

      # Create a mask for points inside the circle
      mask = x**2 + y**2 <= radius**2

      # Apply the mask to the x and y coordinates
      x, y = x[mask], y[mask]
      x = np.concatenate([x, radius * np.cos(angles)])
      y = np.concatenate([y, radius * np.sin(angles)])

      # Compute the z coordinates
      z = surf.profile.sag(x, y) + z_bias
      # Create a mask for points where z is less than or equal to z_bias + sm.gaps[surf_num].thi
      mask = z <= z_bias + sm.gaps[surf_num].thi

      # Apply the mask to the x, y, and z coordinates
      x, y, z = x[mask], y[mask], z[mask]

      # Create masks for positive and negative y values
      posy_mask = y >= 0

      # Apply the masks to the x, y, and z coordinates
      x_pos, y_pos, z_pos = x[posy_mask], y[posy_mask], z[posy_mask]
    
      points = np.vstack([x_pos, y_pos]).T
      tri = Delaunay(points)
      i, j, k = tri.simplices.T
      data.append(go.Mesh3d(x=x_pos, y=z_pos, z=y_pos, i=i, j=j, k=k, color='lightblue', opacity=0.5, visible= visibility))
      data.append(go.Mesh3d(x=x_pos, y=z_pos, z=-y_pos, i=i, j=j, k=k, color='lightblue', opacity=0.5, visible= visibility))
      
    
      x_ang = radius * np.cos(angles)
      y_ang = radius * np.sin(angles)    
      # Compute the z coordinates
      z = surf.profile.sag(x_ang, y_ang) + z_bias

      # Append the coordinates to volume_mesh
      volume_mesh[0].extend(x_ang)
      volume_mesh[1].extend(y_ang)
      volume_mesh[2].extend(z)

      z_bias +=  sm.gaps[surf_num].thi


      if all([len(array) == 0 for array in prev_mesh]):
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
        print(x,y,z)
        data.append(go.Mesh3d(x=x, y=z, z=y, i=i, j=j, k=k, color='lightblue', opacity=0.5, visible= True))
        data.append(go.Mesh3d(x=x, y=z, z=-y, i=i, j=j, k=k, color='lightblue', opacity=0.5, visible= True))
        lens = False
      
    return data