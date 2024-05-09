import dash
import dash_ace
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import numpy as np
from rayoptics.environment import *
from visualize.lens import visualize_lens
from visualize.rays import visualize_rays

wv = 587.5618

app = dash.Dash(__name__)
server = app.server


app.layout = html.Div([
    dcc.Loading(
        id="loading",
        type="circle",  # or "cube", "default"
        fullscreen=False,
        children=[
            html.Div([
            html.Label('Example Models'),
            dcc.Dropdown(id = 'model_option', options =  [{'label': 'OPTI_517', 'value': 'opti_517'},{'label': 'Paralell Zoom','value': 'p_zoom'}, {'label': 'Custom', 'value': 'custom'}], value = 'custom'),
            html.Label('Lens Code'),
            dash_ace.DashAceEditor(
                id='code',
                value="",
                theme='monokai',
                mode='python',
                height='350px',
                width='100%'
            ),
            html.Br(),
            html.Label('Ray Type'),
            dcc.Dropdown(id='ray_option', options=[{'label': 'Paralell', 'value': 'Paralell'}, {'label': 'Point Source', 'value': 'Point Source'}], value = 'Paralell'),
            html.Label('Ray Angle'),
            dcc.Slider(id='ray_mult', min=0, max=1, value=0.5, step=None),
            html.Label('Initial Gap'),
            dcc.Slider(id='init_gap', min=0, max=50, value=1, step=None),
            html.Label('Lens Radius'),
            dcc.Slider(id='rad', min=0, max=10, value=2, step=None),
            html.Label('Increase Focal Distance'),
            dcc.Slider(id='focal', min=0, max=10, value=0, step=None),
            html.Button('Run', id='run_button', style={'margin': '10px'}), 
            ], style={'width': '49%', 'display': 'inline-block'}),

            html.Div([
            html.Label('Optical Model'),
            dcc.Graph(id='figure')
            ], style={'width': '49%', 'display': 'inline-block', 'float': 'right'})
         ]
    )
])
@app.callback(
    Output('code', 'value'),
    [Input('model_option','value')]
)
def update_editor(model_option):
    if model_option == 'opti_517':
        return """# add the surfaces
sm.add_surface([23.713, 4.831, 'N-LAK9', 'Schott'])
sm.add_surface([7331.288, 5.86])
sm.add_surface([-24.456, .975, 'N-SF5,Schott'])
sm.add_surface([21.896, 4.822])
sm.add_surface([86.759, 3.127, 'N-LAK9', 'Schott'])
sm.add_surface([-20.4942, 41.2365]) 
"""
    elif model_option == 'p_zoom':
        return """# add the surfaces
pupil_r = 1.5
n = 1.5
# Do not adjust above values
R2 = -8 
zoom_adjust = -0.25 # Choose either -0.25 or 0 or 0.5

sm.add_surface([-R2, 1, n, pupil_r])
sm.set_stop()
sm.add_surface([R2, 1+zoom_adjust, n-0.5, pupil_r])
sm.set_stop()
sm.add_surface([R2+3, 0, n+0.5, pupil_r])
sm.set_stop()
sm.add_surface([-R2-3, 1, n-0.5, pupil_r])
sm.set_stop()
sm.add_surface([-R2, 1, n, pupil_r])
sm.set_stop()
sm.add_surface([R2, 1.75, n-0.5, pupil_r])
sm.set_stop()
sm.add_surface([-R2-3, 1.7, n, pupil_r])
sm.set_stop()
if zoom_adjust > 0:
    sm.add_surface([R2+3, 1, n-0.5, pupil_r])
    sm.set_stop()
elif zoom_adjust == 0:
    sm.add_surface([R2+3, 1.5, n-0.5, pupil_r])
    sm.set_stop()
else:
    sm.add_surface([R2+3, 1.6, n-0.5, pupil_r])
    sm.set_stop()"""
    else:
        return ""

@app.callback(
    Output('figure', 'figure'),
    [Input('run_button', 'n_clicks')],
    [State('ray_option', 'value'), State('ray_mult', 'value'), State('init_gap', 'value'), State('code', 'value'), State('rad', 'value'), State('focal','value')])
def update_figure(run_clicks, ray_option, ray_mult, init_gap, code, rad, focal):
    # Your code to update the figure goes here
    # You'll need to use the inputs to determine what to do
    # For example, if run_clicks > 0, you might want to execute the code
    # If reset_clicks > 0, you might want to reset the model
    # You'll use ray_option and ray_mult to determine how to visualize the rays
    # And you'll use init_gap to set the initial gap
    # Finally, you'll return the figure
    figure = go.Figure()
    if run_clicks:
        # create a new optical model and set up aliases
        opm = OpticalModel()
        sm = opm['seq_model']
        osp = opm['optical_spec']

        # define field specs
        osp['pupil'] = PupilSpec(osp, key=['object', 'pupil'], value=12.5)
        osp['fov'] = FieldSpec(osp, key=['object', 'angle'], value=20, flds=[0, 0.707, 1], is_relative=True)
        osp['wvls'] = WvlSpec([('F', 0.5), (587.5618, 1.0), ('C', 0.5)], ref_wl=1)
        sm.gaps[0].thi = init_gap
        opm.radius_mode = True
        exec(code)
        sm.gaps[-1].thi = sm.gaps[-1].thi + focal
        opm.update_model()
        data = visualize_lens(sm, 15, rad)
        if ray_option == "Paralell":
            data.extend(visualize_rays(sm,0, rad, wv,x_offsets=np.linspace(-rad + 0.5,rad - 0.5,5), y_offsets=np.linspace(-rad + 0.5,rad - 0.5,5), color = "red"))
        else:
            data.extend(visualize_rays(sm,np.pi * ray_mult, rad, wv, color = "red", num_rays = 10))
        figure = go.Figure(data = data)
        figure.update_scenes(aspectmode='data')
        # Update the size of the chart
        figure.update_layout(
            autosize=True,
            showlegend = False,
            height=600,
            margin=dict(
                l=0,  # left margin
                r=0,  # right margin
                b=0,  # bottom margin
                t=0,  # top margin
                pad=10  # padding
            )
        )
        
    return figure
     

if __name__ == '__main__':
    app.run_server(debug=True, port=8050, host= '0.0.0.0')