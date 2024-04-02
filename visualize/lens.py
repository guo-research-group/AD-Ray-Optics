"""
This file contains the function visualize_lens, which visualizes a lens system by creating a 3D mesh for each surface in the system.
Date: 01/10/2024
Code Author: Alan Fu
"""
import plotly.graph_objects as go
from scipy.spatial import *
import numpy as np
def visualize_lens(sm, N, sd):
    """
    This function visualizes a lens system by creating a 3D mesh for each surface in the system.

    Parameters:
    sm (System): The optical system to visualize.
    N (int): The number of points along each axis to use for the mesh. The total number of points is N^2.
    sd (float): The semi-diameter of the lens. This is used to determine the range of the mesh.

    Returns:
    data (list): A list of plotly Mesh3d objects, one for each surface in the system.

    The function works by iterating over each surface in the system, creating a mesh of points on the surface,
    and then using Delaunay triangulation to create a 3D mesh from these points. The mesh is then added to the
    data list, which is returned at the end of the function.
    """
    z_bias = sm.gaps[0].thi # Z coord of Lens
    data = []               # Lens visualisation data

    #Goes through each surface and collects mesh data
    for i in range(1, sm.get_num_surfaces()-1):
      mesh = [[],[],[]]
      surf = sm.ifcs[i]
      sd = np.max([surf.surface_od(),sd])
      #print(np.linspace(-sd,sd,50))
      for xj in np.linspace(-sd, sd, N):
        for yk in np.linspace(-sd,sd, N):
            z = surf.profile.sag(xj,yk) + z_bias
            #if (z_bias +  sm.gaps[i].thi >= z):
            mesh[0].append(xj)
            mesh[1].append(yk)
            mesh[2].append(z)

      z_bias +=  sm.gaps[i].thi


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
      data.append(go.Mesh3d(x=x, y=z, z=y, i=i, j=j, k=k, intensity=x, colorscale='algae', opacity=0.8))

    return data