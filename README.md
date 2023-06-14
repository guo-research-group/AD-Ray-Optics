# AD Ray-Optics : A Differentiable Ray Tracing Framework
Ray Optics is a Python geometrical optics and image forming optics library. Though it provides a geometric ray tracing foundation for an optical system but the original Ray Optics does not come with auto differentiation feature.
This Differentiable Ray Optics library is based on original Ray Optics and modified using Google-Jax to make it auto differentiable.
Differentiable Ray Optics provides : 
* Validated, auto-differentiable (AD) framework for optical systems built on numpy and Google-Jax
* Low Computational cost 

## Benefits of Using Differentiable Ray Optics 
In Ray Tracing, conventional gradient calculation techniques become computationally expensive when number of parameters in an optical system goes high.
In Automatic Differentiation optical parameters are calculated together with gradient.This helps to improve speed and accuracy of common optical design tasks.

Without Gradient| With Gradient
-------------|-----------------
Optical Parameters: 5 | Optical Parameters: 5
Time taken : 15 minutes | Time taken : 24 secs
## Usage and Documentation
For usage and documentation, a readthedocs page is in active development. Examples for optical system design are provided in Ray-Optics/Examples/. Additional examples will be provided in the future (we welcome community made examples). 

### a) Install and Run Differentiable Ray Optics on Google Colab
Differentiable Ray Optics can be easily installed on Google Colab. 

`!git clone https://github.itap.purdue.edu/guo-research-group/Ray-Optics`

`%cd /content/Ray-Optics`

`!python setup.py develop`

### b) Install and run Locally 
AD Ray-Optics library is tested in Linux environment as Jax libraries can be installed only in Linux. Windows users can use JAX on CPU and GPU via the Windows Subsystem for Linux.

`git clone https://github.itap.purdue.edu/guo-research-group/Ray-Optics`

`cd Ray-Optics`

`python setup.py develop`

For additional dependencies : 
You can then install additional dependencies via 

`pip install -r requirements.txt`

Details on Jax installation can be found https://github.com/google/jax

## Examples
[Demo Lens shape optimization with Installation Guide](https://colab.research.google.com/drive/1FdzNLfRtQDwqgn2NaoXE_66t68sRPzAv?authuser=2#scrollTo=wrTXUUlk5Cmk)

[Demo Flat Lens shape optimization](https://colab.research.google.com/drive/1578cQ-ZtrGUE3I22Gxmwu1MA_TaVQZd2)

