# AD Ray-Optics : A Differentiable Ray Tracing Framework
Auto Differentiable Ray Optics (AD Ray-Optics), a computationally efficient framework for differentiable ray tracing on multi-layer refractive and diffractive optics design. It builds on the existing Python Ray Optics Library and Google Jax.
Given the sequential model of a lens design, AD Ray Optics precompiles a computational graph that computes gradients of light rays via automatic differentiation. In contrast to finite difference, which becomes computationally expensive when the number of parameters in an optical system becomes high, and is prone to numerical error, the proposed automatic differentiation framework improves the speed and stability of calculating gradients. We validate AD Ray-Optics against finite difference gradient calculation through experiments and show that AD Ray-Optics achieves at least 30 times faster speed than finite difference gradient calculation. We demonstrate several use cases of AD Ray-Optics, including single lens optimization, cascade lens optimization, and hybrid
refractive and diffractive optics optimization. It could be a useful computational backbone for endtoend computational imaging and photography.

![Image model ](https://github.com/guo-research-group/AD-Ray-Optics/blob/main/image%20model.JPG)


## Benefits of Using Differentiable Ray Optics 
* Based on Numpy and Jax
* Computationally Efficient
* Compatible with both refractive and diffractive optics. 
  
## Results

* Performance comparison between finite difference and automatic differentiation. Time to optimize the lens parameters using auto diff 
  linearly increases with the number of parameters.
  
![comparison](https://github.com/guo-research-group/AD-Ray-Optics/blob/main/No%20of%20Parameters%20vs%20Time.png)

* Optimization of 4 flat Lenses with zoom effect

![lenses](https://github.com/guo-research-group/AD-Ray-Optics/blob/main/pic.JPG)

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
