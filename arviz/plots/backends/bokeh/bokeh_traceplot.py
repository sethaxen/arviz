"""Bokeh Traceplot."""
import bokeh.plotting as bkp
from bokeh.models import ColumnDataSource, Span
from bokeh.models.annotations import Title
from bokeh.layouts import gridplot
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np

from ....data import convert_to_dataset
from ...distplot import plot_dist
from ...plot_utils import _scale_fig_size, get_bins, xarray_var_iter, make_label, get_coords
from ....utils import _var_names
from ....rcparams import rcParams


def _plot_trace_bokeh(
    data,
    var_names=None,
    coords=None,
    divergences="bottom",
    figsize=None,
    textsize=None,
    lines=None,
    compact=False,
    combined=False,
    legend=False,
    plot_kwargs=None,
    fill_kwargs=None,
    rug_kwargs=None,
    hist_kwargs=None,
    trace_kwargs=None,
    backend_kwargs=None,
    show=True,
):
    """Plot distribution (histogram or kernel density estimates) and sampled values.

    NOTE: EXPERIMENTAL CODE

    Not implemented:
        If `divergences` data is available in `sample_stats`, will plot the location of divergences as
        dashed vertical lines.

    Parameters
    ----------
    data : obj
        Any object that can be converted to an az.InferenceData object
        Refer to documentation of az.convert_to_dataset for details
    var_names : string, or list of strings
        One or more variables to be plotted.
    coords : mapping, optional
        Coordinates of var_names to be plotted. Passed to `Dataset.sel`
    divergences : {"bottom", "top", None, False}
        NOT IMPLEMENTED
        Plot location of divergences on the traceplots. Options are "bottom", "top", or False-y.
    figsize : figure size tuple
        If None, size is (12, variables * 2)
    textsize: float
        Text size scaling factor for labels, titles and lines. If None it will be autoscaled based
        on figsize.
    lines : tuple
        Tuple of (var_name, {'coord': selection}, [line, positions]) to be overplotted as
        vertical lines on the density and horizontal lines on the trace.
    compact : bool
        Plot multidimensional variables in a single plot.
    combined : bool
        Flag for combining multiple chains into a single line. If False (default), chains will be
        plotted separately.
    legend : bool
        Add a legend to the figure with the chain color code.
    plot_kwargs : dict
        Extra keyword arguments passed to `arviz.plot_dist`. Only affects continuous variables.
    fill_kwargs : dict
        Extra keyword arguments passed to `arviz.plot_dist`. Only affects continuous variables.
    rug_kwargs : dict
        Extra keyword arguments passed to `arviz.plot_dist`. Only affects continuous variables.
    hist_kwargs : dict
        Extra keyword arguments passed to `arviz.plot_dist`. Only affects discrete variables.
    trace_kwargs : dict
        Extra keyword arguments passed to `bokeh.plotting.lines`
    backend_kwargs : dict
        Extra keyword arguments passed to `bokeh.plotting.figure`
    show : bool
        Call `bokeh.plotting.show` for gridded plots `bokeh.layouts.gridplot(axes.tolist())`
    Returns
    -------
    ndarray
        axes (bokeh figures)


    Examples
    --------
    Plot a subset variables

    .. plot::
        :context: close-figs

        >>> import arviz as az
        >>> data = az.load_arviz_data('non_centered_eight')
        >>> coords = {'school': ['Choate', 'Lawrenceville']}
        >>> az.plot_trace(data, var_names=('theta_t', 'theta'), coords=coords)

    Show all dimensions of multidimensional variables in the same plot

    .. plot::
        :context: close-figs

        >>> az.plot_trace(data, compact=True)

    Combine all chains into one distribution

    .. plot::
        :context: close-figs

        >>> az.plot_trace(data, var_names=('theta_t', 'theta'), coords=coords, combined=True)


    Plot reference lines against distribution and trace

    .. plot::
        :context: close-figs

        >>> lines = (('theta_t',{'school': "Choate"}, [-1]),)
        >>> az.plot_trace(data, var_names=('theta_t', 'theta'), coords=coords, lines=lines)

    """
    if divergences:
        try:
            divergence_data = convert_to_dataset(data, group="sample_stats").diverging
        except (ValueError, AttributeError):  # No sample_stats, or no `.diverging`
            divergences = False

    if coords is None:
        coords = {}

    data = get_coords(convert_to_dataset(data, group="posterior"), coords)
    var_names = _var_names(var_names, data)

    if divergences:
        divergence_data = get_coords(
            divergence_data, {k: v for k, v in coords.items() if k in ("chain", "draw")}
        )

    if lines is None:
        lines = ()

    num_colors = len(data.chain) + 1 if combined else len(data.chain)
    colors = [
        prop
        for _, prop in zip(
            range(num_colors), cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])
        )
    ]

    if compact:
        skip_dims = set(data.dims) - {"chain", "draw"}
    else:
        skip_dims = set()

    plotters = list(xarray_var_iter(data, var_names=var_names, combined=True, skip_dims=skip_dims))
    max_plots = rcParams["plot.max_subplots"]
    max_plots = len(plotters) if max_plots is None else max_plots
    if len(plotters) > max_plots:
        warnings.warn(
            "rcParams['plot.max_subplots'] ({max_plots}) is smaller than the number "
            "of variables to plot ({len_plotters}), generating only {max_plots} "
            "plots".format(max_plots=max_plots, len_plotters=len(plotters)),
            SyntaxWarning,
        )
        plotters = plotters[:max_plots]

    if figsize is None:
        figsize = (12, len(plotters) * 2)

    if trace_kwargs is None:
        trace_kwargs = {}

    trace_kwargs.setdefault("alpha", 0.35)

    if hist_kwargs is None:
        hist_kwargs = {}
    if plot_kwargs is None:
        plot_kwargs = {}
    if fill_kwargs is None:
        fill_kwargs = {}
    if rug_kwargs is None:
        rug_kwargs = {}

    hist_kwargs.setdefault("alpha", 0.35)

    figsize, _, titlesize, xt_labelsize, linewidth, _ = _scale_fig_size(
        figsize, textsize, rows=len(plotters), cols=2
    )
    figsize = int(figsize[0] * 90 // 2), int(figsize[1] * 90 // len(plotters))

    trace_kwargs.setdefault("line_width", linewidth)
    plot_kwargs.setdefault("line_width", linewidth)

    if backend_kwargs is None:
        backend_kwargs = dict()

    backend_kwargs.setdefault(
        "tools",
        ("pan,wheel_zoom,box_zoom," "lasso_select,poly_select," "undo,redo,reset,save,hover"),
    )
    backend_kwargs.setdefault("output_backend", "webgl")
    backend_kwargs.setdefault("height", figsize[1])
    backend_kwargs.setdefault("width", figsize[0])

    axes = []
    for i in range(len(plotters)):
        if i != 0:
            _axes = [
                bkp.figure(**backend_kwargs),
                bkp.figure(x_range=axes[0][1].x_range, **backend_kwargs),
            ]
        else:
            _axes = [bkp.figure(**backend_kwargs), bkp.figure(**backend_kwargs)]
        axes.append(_axes)

    axes = np.array(axes)

    # THIS IS BROKEN --> USE xarray_sel_iter
    cds_data = {}
    draw_name = "draw"
    for var_name, _, value in plotters:
        for chain_idx, _ in enumerate(data.chain.values):
            if chain_idx not in cds_data:
                cds_data[chain_idx] = {}
            cds_data[chain_idx][var_name] = data[var_name][chain_idx].values

    while any(key == draw_name for key in cds_data[0]):
        draw_name += "w"

    for chain_idx in cds_data:
        cds_data[chain_idx][draw_name] = data.draw.values

    cds_data = {chain_idx: ColumnDataSource(cds) for chain_idx, cds in cds_data.items()}

    for idx, (var_name, selection, value) in enumerate(plotters):
        value = np.atleast_2d(value)

        if len(value.shape) == 2:
            _plot_chains_bokeh(
                axes[idx, 0],
                axes[idx, 1],
                cds_data,
                draw_name,
                var_name,
                colors,
                combined,
                legend,
                xt_labelsize,
                trace_kwargs,
                hist_kwargs,
                plot_kwargs,
                fill_kwargs,
                rug_kwargs,
            )
        else:
            value = value.reshape((value.shape[0], value.shape[1], -1))
            for sub_idx in range(value.shape[2]):
                _plot_chains_bokeh(
                    axes[idx, 0],
                    axes[idx, 1],
                    cds_data,
                    draw_name,
                    var_name,
                    colors,
                    combined,
                    legend,
                    xt_labelsize,
                    trace_kwargs,
                    hist_kwargs,
                    plot_kwargs,
                    fill_kwargs,
                    rug_kwargs,
                )

        for col in (0, 1):
            _title = Title()
            _title.text = make_label(var_name, selection)
            axes[idx, col].title = _title

        for _, _, vlines in (j for j in lines if j[0] == var_name and j[1] == selection):
            if isinstance(vlines, (float, int)):
                line_values = [vlines]
            else:
                line_values = np.atleast_1d(vlines).ravel()

            for line_value in line_values:
                vline = Span(
                    location=line_value,
                    dimension="height",
                    line_color="black",
                    line_width=1.5,
                    line_alpha=0.75,
                )
                hline = Span(
                    location=line_value,
                    dimension="width",
                    line_color="black",
                    line_width=1.5,
                    line_alpha=trace_kwargs["alpha"],
                )

                axes[idx, 0].renderers.append(vline)
                axes[idx, 1].renderers.append(hline)

        if legend:
            for col in (0, 1):
                axes[idx, col].legend.location = "top_left"
                axes[idx, col].legend.click_policy = "hide"
        else:
            for col in (0, 1):
                axes[idx, col].legend.visible = False

    if show:
        grid = gridplot([list(item) for item in axes], toolbar_location="above")
        bkp.show(grid)

    return axes


def _plot_chains_bokeh(
    ax_density,
    ax_trace,
    data,
    x_name,
    y_name,
    colors,
    combined,
    xt_labelsize,
    legend,
    trace_kwargs,
    hist_kwargs,
    plot_kwargs,
    fill_kwargs,
    rug_kwargs,
):
    marker = trace_kwargs.pop("marker", True)
    for chain_idx, cds in data.items():
        # do this manually?
        # https://stackoverflow.com/questions/36561476/change-color-of-non-selected-bokeh-lines
        if legend:
            ax_trace.line(
                x=x_name,
                y=y_name,
                source=cds,
                line_color=colors[chain_idx],
                legend_label="chain {}".format(chain_idx),
                **trace_kwargs
            )
            if marker:
                ax_trace.circle(
                    x=x_name,
                    y=y_name,
                    source=cds,
                    radius=0.48,
                    line_color=colors[chain_idx],
                    fill_color=colors[chain_idx],
                    alpha=0.5,
                )
        else:
            # tmp hack
            ax_trace.line(
                x=x_name, y=y_name, source=cds, line_color=colors[chain_idx], **trace_kwargs
            )
            if marker:
                ax_trace.circle(
                    x=x_name,
                    y=y_name,
                    source=cds,
                    radius=0.48,
                    line_color=colors[chain_idx],
                    fill_color=colors[chain_idx],
                    alpha=0.5,
                )
        if not combined:
            if legend:
                plot_kwargs["legend_label"] = "chain {}".format(chain_idx)
            plot_kwargs["line_color"] = colors[chain_idx]
            plot_dist(
                cds.data[y_name],
                textsize=xt_labelsize,
                ax=ax_density,
                color=colors[chain_idx],
                hist_kwargs=hist_kwargs,
                plot_kwargs=plot_kwargs,
                fill_kwargs=fill_kwargs,
                rug_kwargs=rug_kwargs,
                backend="bokeh",
                show=False,
            )

    if combined:
        plot_dist(
            np.concatenate(
                [item for _data in data.values() for item in _data.data[y_name].values]
            ).flatten(),
            textsize=xt_labelsize,
            ax=ax_density,
            color=colors[-1],
            hist_kwargs=hist_kwargs,
            plot_kwargs=plot_kwargs,
            fill_kwargs=fill_kwargs,
            rug_kwargs=rug_kwargs,
            backend="bokeh",
            show=False,
        )
