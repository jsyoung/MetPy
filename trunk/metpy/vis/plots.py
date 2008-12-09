__all__ = ['meteogram', 'station_plot']

from datetime import timedelta
from pytz import UTC
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
from matplotlib.dates import (DateFormatter, HourLocator, AutoDateLocator,
    date2num)
from metpy.cbook import iterable

#Default units for certain variables
default_units = {'temperature':'C', 'dewpoint':'C', 'relative humidity':'%',
    'pressure':'mb', 'wind speed':'m/s', 'solar radiation':'$W/m^2$',
    'rainfall':'mm', 'wind gusts':'m/s'}

def _rescale_yaxis(ax, bounds):
    # Manually tweak the limits here to ignore the low bottom set
    # for fill_between
    XY = np.array([[0]*len(bounds), bounds]).T
    ax.ignore_existing_data_limits = True
    ax.update_datalim(XY, updatex=False, updatey=True)
    ax.autoscale_view()

#TODO: REWRITE AS CLASS
def meteogram(data, fig=None, num_panels=5, time_range=None, ticker=None,
    layout=None, styles=None, limits=None, units=None, field_info=None):
    '''
    Plots a meteogram (collection of time series) for a data set. This
    is broken down into a series of panels (defaults to 3), each of which
    can plot multiple variables, with sensible defaults, but can also be
    specified using *layout*.

    *data* : numpy record array
        A numpy record array containing time series for individual variables
        in each field.

    *fig* : :class:`matplotlib.figure.Figure` instance or None.
        A matplotlib Figure on which to draw.  If None, a new figure
        will be created.

    *num_panels* : int
        The number of panels to use in the plot.

    *time_range* : sequence, datetime.timedetla, or *None*
        If a sequence, the starting and ending times for the x-axis.  If
        a :class:`datetime.timedelta` object, it represents the time span
        to plot, which will end with the last data point.  It defaults to
        the last 24 hours of data.

    *ticker* : :class:`matplotlib.dates.DateLocator`
        An instance of a :class:`matplotlib.dates.DateLocator` that controls
        where the ticks will be located.  The default is
        :class:`matplotlib.dates.AutoDateLocator`.

    *layout* : dictionary
        A dictionary that maps panel numbers to lists of variables.
        If a panel is not found in the dictionary, a default (up to panel 5)
        will be used.  *None* can be included in the list to denote that
        :func:`pyplot.twinx` should be called, and the remaining variables
        plotted.

    *styles* : dictionary
        A dictionary that maps variable names to dictionary of matplotlib
        style arguments.  Also, the keyword `fill` can be included, to
        indicate that a filled plot should be used.  Any variable not
        specified will use a default (if available).

    *limits* : dictionary
        A dictionary that maps variable names to plot limits.  These limits
        are given by tuples with at least two items, which specify the
        start and end limits.  Either can be *None* which implies using the
        automatically determined value.  Optional third and fourth values
        can be given in the tuple, which is a list of tick values and labels,
        respectively.

    *units* : dictionary
        A dictionary that maps variable names to unit strings for axis labels.

    *field_info* : dictionary
        A dictionary that maps standard names, like 'temperature' or
        'dewpoint' to the respective variables in the data record array.

    Returns : list
        A list of the axes objects that were created.
    '''

    if fig is None:
        fig = plt.figure()

    if field_info is None:
        field_info = {}

    inv_field_info = dict(zip(field_info.values(), field_info.keys()))

    def map_field(name):
        return field_info.get(name, name)

    def inv_map_field(name):
        return inv_field_info.get(name, name)

    #Get the time variable, using field info if necessary
    dt = map_field('datetime')
    time = data[dt]
    tz = UTC

    #Process time_range.
    if time_range is None:
        time_range = timedelta(hours=24)
        if ticker is None:
            ticker = HourLocator(byhour=np.arange(0, 25, 3), tz=tz)

    #Process ticker
    if ticker is None:
        ticker = AutoDateLocator(tz=tz)

    if not iterable(time_range):
        end = time[-1]
        start = end - time_range
        time_range = (start, end)

    #List of variables in each panel.  None denotes that at that point, twinx
    #should be called and the remaining variables plotted on the other axis
    default_layout = {
        0:[map_field('temperature'), map_field('dewpoint')],
        1:[map_field('wind gusts'), map_field('wind speed'), None,
            map_field('wind direction')],
        2:[map_field('pressure')],
        3:[map_field('rainfall')],
        4:[map_field('solar radiation')]}

    if layout is not None:
        default_layout.update(layout)
    layout = default_layout

    #Default styles for each variable
    default_styles = {
        map_field('relative humidity'):dict(color='green', linestyle='--'),
        map_field('dewpoint'):dict(facecolor='green', edgecolor='None',
            fill=True),
        map_field('temperature'):dict(facecolor='red', edgecolor='None',
            fill=True),
        map_field('pressure'):dict(facecolor='brown', edgecolor='None',
            fill=True),
        map_field('dewpoint'):dict(facecolor='green', edgecolor='None',
            fill=True),
        map_field('wind speed'):dict(facecolor='blue', edgecolor='None',
            fill=True),
        map_field('wind gusts'):dict(facecolor='lightblue', edgecolor='None',
            fill=True),
        map_field('wind direction'):dict(markeredgecolor='goldenrod',
            marker='o', linestyle='', markerfacecolor='None',
            markeredgewidth=1),
        map_field('rainfall'):dict(facecolor='lightgreen', edgecolor='None',
            fill=True),
        map_field('solar radiation'):dict(facecolor='orange', edgecolor='None',
            fill=True),
        map_field('windchill'):dict(color='lightblue')}

    if styles is not None:
        default_styles.update(styles)
    styles = default_styles

    #Default data limits
    default_limits = {
        map_field('wind direction'):(0, 360, np.arange(0,400,45),
            ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']),
        map_field('wind speed'):(0, None),
        map_field('wind gusts'):(0, None),
        map_field('rainfall'):(0, None),
        map_field('solar radiation'):(0, 1000, np.arange(0,1050,200))
        }

    if limits is not None:
        default_limits.update(limits)
    limits = default_limits

    #Set data units
    def_units = default_units.copy()
    if units is not None:
        def_units.update(units)
    units = def_units

    #Get the station name, using field info if necessary
    site_name = map_field('site')
    site = data[site_name][0]

    #Get the date from the first time
    date = time_range[0].strftime('%Y-%m-%d')

    axes = []
    for panel in range(num_panels):
        if panel > 0:
            ax = fig.add_subplot(num_panels, 1, panel+1, sharex=ax)
        else:
            ax = fig.add_subplot(num_panels, 1, panel+1)
            ax.set_title('Meteogram for %s on %s' % (site, date))

        panel_twinned = False

        var_min = []
        var_max = []
        for varname in layout[panel]:
            if varname is None:
                _rescale_yaxis(ax, var_min + var_max)
                ax = ax.twinx()
                panel_twinned = True
                var_min = []
                var_max = []
                continue

            # Get the linestyle for this variable
            style = styles.get(varname, dict())

            #Get the variable from the data and plot
            var = data[map_field(varname)]

            #Set special limits if necessary
            lims = limits.get(varname, (None, None))

            #Store the max and min for auto scaling
            var_max.append(var.max())
            var_min.append(var.min())

            if style.pop('fill', False):
                #Plot the filled area.  Need latest Matplotlib for date support
                #with fill_betweeen
                lower = -500 if lims[0] is None else lims[0]
                ax.fill_between(time, lower, var, where=~var.mask, **style)
                _rescale_yaxis(ax, var_min + var_max)
            else:
                ax.plot(time, var, **style)

            #If then length > 2, then we have ticks and (maybe) labels
            if len(lims) > 2:
                other = lims[2:]
                lims = lims[:2]
                #Separate out the ticks and perhaps labels
                if len(other) == 1:
                    ax.set_yticks(other[0])
                else:
                    ticks,labels = other
                    ax.set_yticks(ticks)
                    ax.set_yticklabels(labels)
            ax.set_ylim(*lims)

            # Set the label to the title-cased nice-version from the
            # field info with units, if given.
            if varname in units and units[varname]:
                unit_str = ' (%s)' % units[varname]
            else:
                unit_str = ''
            ax.set_ylabel(inv_map_field(varname).title() + unit_str)

        ax.xaxis.set_major_locator(ticker)
        ax.xaxis.set_major_formatter(DateFormatter('%H'))
        if not panel_twinned:
            ax.yaxis.set_ticks_position('both')
            for tick in ax.yaxis.get_major_ticks():
                tick.label2On = True
        axes.append(ax)
    ax.set_xlabel('Hour (%s)' % tz.tzname(time[0]))
    ax.set_xlim(*time_range)

    return axes

def text_plot(ax, x, y, data, format='%.0f', loc=None, **kw):
    from matplotlib.cbook import delete_masked_points
    from matplotlib import transforms

    # Default to centered on point
    if loc is not None:
        x0,y0 = loc
        trans = ax.transData + transforms.Affine2D().translate(x0, y0)
    else:
        trans = ax.transData

    # Handle masked arrays
    x,y,data = delete_masked_points(x, y, data)

    #Calculate the offset
    for xi, yi, d in zip(x, y, data):
        ax.text(xi, yi, format % d, transform=trans, ha='center', va='center',
            clip_on=True, **kw)

#Maps specifiers to normalized offsets in x and y
direction_map = dict(N=(0,1), NE=(1,1), E=(1,0), SE=(1,-1), S=(0,-1),
    SW=(-1,-1), W=(-1,0), NW=(-1,1), C=(0,0))

def station_plot(data, ax=None, basemap=None, layout=None, styles=None,
    offset=10., field_info=None):
    '''
    Makes a station plot of the variables in data.

    *data* : numpy record array
        A numpy record array containing time series for individual variables
        in each field.

    *ax* : :class:`matplotlib.axes.Axes` instance or None
        The matplotlib Axes object on which to draw the station plot.  If None,
        the current Axes object is used.

    *basemap* : :class:`mpl_toolkits.basemap.Basemap` instance or None
        A Basemap object to use to convert geographic coordinates.  If None,
        the geographic coordinates are used, as is, without any projection.

    *layout* : dictionary
        A dictionary that maps locations to field names.  Valid locations are:
        ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'C'], where 'C' represents
        the center location, and all others represent cardinal directions
        relative to the center point.  The actual distance from the center
        is controlled by *offset*.

    *styles* : dictionary
        A dictionary that maps variable names to dictionary of matplotlib
        text style arguments. Any variable not specified will use a
        default (if available).

    *offset* : float
        The offset, in pixels, from the center point for the values being
        plotted.

    *field_info* : dictionary
        A dictionary that maps standard names, like 'temperature' or
        'dewpoint' to the respective variables in the data record array.
    '''
    if ax is None:
        ax = plt.gca()

    #If we don't get a basemap converter, make it a do-nothing function
    if basemap is None:
        basemap = lambda x,y:x,y

    if field_info is None:
        field_info = {}

    inv_field_info = dict(zip(field_info.values(), field_info.keys()))

    def map_field(name):
        return field_info.get(name, name)

    def inv_map_field(name):
        return inv_field_info.get(name, name)

    #Update the default layout with the passed in one
    #TODO: HOW DO WE SPECIFY BARBS?
    default_layout=dict(NW=map_field('temperature'), SW=map_field('dewpoint'),
        C=None)
    if layout is not None:
        default_layout.update(layout)
        layout = default_layout

    default_styles=dict()
    if styles is not None:
        default_styles.update(styles)
        styles = default_styles

    if (map_field('u') in data.dtype.names and
        map_field('v') in data.dtype.names):
        u = data[map_field('u')]
        v = data[map_field('v')]
    else:
        wspd = data[map_field('wind speed')]
        wdir = data[map_field('wind direction')]
        u,v = get_wind_components(wspd, wdir)

    #Convert coordinates
    x,y = basemap(data[map_field('longitude')], data[map_field('latitude')])

    # plot barbs.
    ax.barbs(x, y, u, v)
    for spot in layout:
        var = layout[spot]
        style = styles.get(var, {})
        text_plot(ax, x, y, data[var], '%.1f', loc=direction_map[spot], **style)
