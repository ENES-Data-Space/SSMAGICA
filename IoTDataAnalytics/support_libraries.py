from ipywidgets import interact, Dropdown, Button, Output
from IPython.display import *
import pandas as pd
import io
from bokeh.io import output_notebook, show
from bokeh.models import ColumnDataSource, GMapOptions, HoverTool, LabelSet, Label, Legend, DatetimeTickFormatter, DatetimeTicker, Range1d
from bokeh.resources import INLINE
from bokeh.plotting import gmap, figure, output_notebook, show, reset_output
from datetime import datetime, timedelta
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

path = './data'
df_TTs = pd.read_csv(f'{path}/sensors.csv', sep=',', usecols=["tree_talker", "latitude", "longitude", "site"])
def getTable(site):
  dfsite = pd.read_csv(f'{path}/{site}_data.csv', dtype={'tt_serial_number':'string'})
  dfsite.index = pd.to_datetime(dfsite['timestamp'])
  dfsite.drop(columns='timestamp', inplace=True)
  return dfsite
sites = ['Avetrana', 'Mesagne']
selected_TTs1 = df_TTs.loc[df_TTs['site'] == 'Avetrana', 'tree_talker']
selected_TTs2 = df_TTs.loc[df_TTs['site'] == 'Mesagne', 'tree_talker']
TTs_for_site={'Avetrana':selected_TTs1,'Mesagne':selected_TTs2}
map_options = GMapOptions(lat=40.45896815300001, lng=17.727795989250005, map_type="satellite", zoom=10)
p = gmap("", map_options, title="TreeTalker map", width = 950)

siteDropdown = Dropdown(description='Site:', options = sites)
button = Button(description="View map")
output = Output()

_MAP_FREQUENCY = {'daily': 'D', 'weekly': 'W', 'monthly': 'M'}
_MAP_LABEL = {'air_temperature': 'Air Temperature (°C)', 'air_humidity': 'Air Humidity (%)', 'sapflow': 'Sap flow density (g/cm2)', 'VPD': 'Vapour pressure deficit (kPa)', 'NDVI': 'Normalized Difference Vegetation Index', 'NPP': 'Net Primary Productivity', 'growth_rate': 'Growth Rate'}
_MAP_COLORS = {'air_temperature': {'max':'#ad1111', 'avg':'#db3609', 'min':'#de7a5f'}, 'air_humidity': {'max':'#3e39bf','avg':'#4c8dcf','min':'#71c0d1'}, 'sapflow': {'max':'#017060','avg':'#02b097','min':'#03fcd9'}, 'VPD': {'max':'#b3ad02','avg':'#d6cf02','min':'#ede61f'}, 'NDVI': {'max':'#207501','avg':'#30b500','min':'#78f74a'}, 'NPP': {'max':'#434d3f','avg':'#708269','min':'#a4bf99'}, 'growth_rate': {'max':'#613b01','avg':'#d96830','min':'#e8b566'}}

def getMap():
  display(siteDropdown, button, output)
  button.on_click(on_button_clicked)

def getTTmap(siteD):
  sel_lat = df_TTs.loc[df_TTs['site'] == siteD, 'latitude']
  sel_lon = df_TTs.loc[df_TTs['site'] == siteD, 'longitude']
  sel_TTs = df_TTs.loc[df_TTs['site'] == siteD, 'tree_talker']
  labels_TTs = (sel_TTs.astype("str").str.center(10, " ")).values
  map_options = GMapOptions(lat=sel_lat.mean(), lng=sel_lon.mean(), map_type="satellite", zoom=19)
  source = ColumnDataSource(
    data=dict(
      lat=sel_lat,
      lon=sel_lon,
      tt_sernum=sel_TTs,
      tt_labels=labels_TTs
  ))
  TOOLTIPS = [('TT serial number', '@tt_sernum')]
  labels = LabelSet(x='lon', y='lat', x_offset=-20, y_offset=8, text_font_size='9px', text='tt_labels', source=source, text_color="black", border_line_color="black", background_fill_color="white", background_fill_alpha=1.0, text_line_height=50, text_baseline="bottom")
  # output_notebook(INLINE)
  p.map_options = map_options
  p.add_tools(HoverTool(tooltips=TOOLTIPS))
  p.add_layout(labels)
  p.diamond(x="lon", y="lat", size=12, fill_color="yellow", line_color="yellow", fill_alpha=0.8, source=source)
  return p

@interact(siteD = siteDropdown)
def print_TT(siteD):
  pass 

def on_button_clicked(b):
    with output:
        clear_output(wait=True)
        map = getTTmap(siteDropdown.value)
        output_notebook()
        show(map)

def reduce(data, metric, frequency, operation=None):
  df = pd.DataFrame()
  if isinstance(data, pd.Series):
    data = data.to_frame()
  if frequency == 'hourly':
    if operation is not None:
      if operation == 'max':
        values = data.groupby(level=0).max()[metric].dropna()
      elif operation == 'avg':
        values = data.groupby(level=0).mean()[metric].dropna()
      elif operation == 'min':
        values = data.groupby(level=0).min()[metric].dropna()
      column = f'{operation}_{metric}'
      df[column] = values
    else:
      max_values = data.groupby(level=0).max()[metric].dropna()
      mean_values = data.groupby(level=0).mean()[metric].dropna()
      min_values = data.groupby(level=0).min()[metric].dropna()
      df[f'max_{metric}'] = max_values
      df[f'avg_{metric}'] = mean_values
      df[f'min_{metric}'] = min_values
  else:
    freq_letter = _MAP_FREQUENCY[frequency]
    if operation is not None:
      if operation == 'max':
        values = data.resample(freq_letter).max()[metric].dropna()
      elif operation == 'avg':
        values = data.resample(freq_letter).mean()[metric].dropna()
      elif operation == 'min':
        values = data.resample(freq_letter).min()[metric].dropna()
      column = f'{operation}_{metric}'
      df[column] = values
    else:
      max_values = data.resample(freq_letter).max()[metric].dropna()
      mean_values = data.resample(freq_letter).mean()[metric].dropna()
      min_values = data.resample(freq_letter).min()[metric].dropna()
      df[f'max_{metric}'] = max_values
      df[f'avg_{metric}'] = mean_values
      df[f'min_{metric}'] = min_values
  return df

def createFigure(labels, source_metrics, metric, frequency, aggregation):
  source = ColumnDataSource(data = source_metrics)
  label = _MAP_LABEL[metric]
  # Set the x_range to the list of categories above
  if frequency == 'hourly':
    date_values = []
    start_date = labels[0]
    end_date = labels[-1]
    delta = timedelta(hours=4)
    while start_date <= end_date:
      date_values.append(start_date)
      start_date += delta
    if len(date_values)>50:
      number_ticks = 50
    elif len(date_values)<15:
      number_ticks = 15
    else: number_ticks = len(date_values)
    p = figure(x_axis_type = 'datetime', y_axis_label = label, plot_height=400, plot_width=950, title=str(frequency).capitalize() + " " + label)
  elif frequency == 'daily':
    date_values = []
    start_date = labels[0]
    end_date = labels[-1]
    delta = timedelta(days=1)
    while start_date <= end_date:
      date_values.append(start_date)
      start_date += delta
    if len(date_values)>50:
      number_ticks = 50
    else: 
      number_ticks = len(date_values)
    p = figure(x_axis_type = 'datetime', y_axis_label = label, plot_height=400, plot_width=950, title=str(frequency).capitalize() + " " + label)
  else:
    p = figure(x_range=labels, y_axis_label = label, plot_height=400, plot_width=950, title=str(frequency).capitalize() + " " + label)

  # Categorical values can also be used as coordinates
  items = []
  lines = {}
  tooltips = []

  if frequency == 'hourly' and aggregation == False:
    p.line(x='time', y=metric, line_width=2, legend_label=metric, color=_MAP_COLORS[metric]['avg'], source=source)
  else:
    for key in source_metrics.keys():
      if key !='time':
        op = key.split('_')[0]
        lines[op] = p.line(x='time', y=key, line_width=2, color=_MAP_COLORS[metric][op], source=source)
        items.append((op, [lines[op]]))
        tooltips.append((op,f'@{key}'))

    # Set legend
    legend = Legend(items=items, location="top_right")
    p.add_layout(legend, 'right')

    # Set some properties to make the plot look better
    if 'max' in lines.keys() and 'min' in lines.keys():
      p.y_range.renderers = [lines['max'], lines['min']]
    if 'avg' in lines.keys():
      r1 = lines['avg']
    else:
      if 'max' in lines.keys():
        r1 = lines['max']
      else:
        r1 = lines['min']

  p.legend.click_policy="hide"
  p.xgrid.grid_line_color = None
  p.xaxis.axis_label = "Time"
  p.xaxis.major_label_orientation = 1.2

  # Add hover tooltip
  if frequency == 'hourly' and aggregation == False:
    x_range = Range1d(labels[0].timestamp()*1000, labels[-1].timestamp()*1000)
    p.x_range= x_range
    p.xaxis.formatter=DatetimeTickFormatter(days="%Y-%m-%d %H", months="%Y-%m-%d %H", hours="%Y-%m-%d %H", minutes="%Y-%m-%d %H")
    p.xaxis.ticker = DatetimeTicker(desired_num_ticks=number_ticks)
    p.add_tools(HoverTool(
      tooltips=[
          ( 'time',  '@time{%F %T}' ),
          ( metric,    f'@{metric}' ),
      ],
      formatters={'@time': 'datetime'},
      mode='vline',
    ))
  elif frequency == 'hourly' and aggregation == True:
    x_range = Range1d(labels[0].timestamp()*1000 - 86400000, labels[-1].timestamp()*1000 + 86400000)
    p.x_range= x_range
    tooltips.append(('time','@time{%F %T}'))
    p.xaxis.formatter=DatetimeTickFormatter(days="%Y-%m-%d %H", months="%Y-%m-%d %H", hours="%Y-%m-%d %H", minutes="%Y-%m-%d %H")
    p.xaxis.ticker = DatetimeTicker(desired_num_ticks=number_ticks)
    p.add_tools(HoverTool(
      tooltips=tooltips,
      formatters={'@time': 'datetime'},
      mode='vline',
      renderers=[r1]
    ))
  elif frequency == 'daily':
    x_range = Range1d(labels[0].timestamp()*1000, labels[-1].timestamp()*1000)
    p.x_range= x_range
    tooltips.append(('time','@time{%F}'))
    p.xaxis.formatter=DatetimeTickFormatter(days="%Y-%m-%d", months="%Y-%m-%d", hours="%Y-%m-%d", minutes="%Y-%m-%d")
    p.xaxis.ticker = DatetimeTicker(desired_num_ticks=number_ticks)
    p.add_tools(HoverTool(
        tooltips=tooltips,
        formatters={'@time': 'datetime'},
        mode='vline',
        renderers=[r1]
    ))
  else:
    tooltips.append(('time','@time'))
    p.add_tools(HoverTool(
        tooltips=tooltips,
        mode='vline',
        renderers=[r1]
    ))
  return p

def getGraph(data, metric, frequency):
  pref_list = ['max', 'avg', 'min']
  labels = []
  aggregation = False
  for t in data.index: 
    if frequency == 'daily':
      t_to_dt = (t.to_pydatetime()).date()
      labels.append(datetime.strptime(str(t_to_dt), '%Y-%m-%d'))
    elif frequency == 'weekly':
      labels.append(str(t.year) + ' ' + str(t.month) + ' ' + str(t.day))
    elif frequency == 'monthly':
      labels.append(str(t.year) + ' ' + str(t.month))
    elif frequency == 'hourly':
      date_hour = str(t.date()) + ' ' + str(t.hour)
      labels.append(datetime.strptime(date_hour, '%Y-%m-%d %H'))

  # Set ColumnDataSource for each metric
  source_metrics = {'time': labels}
  if frequency == 'hourly':
    if isinstance(data, pd.DataFrame):
      for column in data:
        source_metrics[column] = data[column].squeeze()
    else:
      source_metrics[data.name] = data.values.tolist()
    for item in source_metrics.keys():
      if list(filter(item.startswith, pref_list)) != []:
        aggregation = True
        break
      else:
        aggregation = False
  else:
    aggregation = True
    for column in data:
      source_metrics[column] = data[column].squeeze()
  pl = createFigure(labels, source_metrics, metric, frequency, aggregation)
  output_notebook()
  show(pl)
