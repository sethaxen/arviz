"""Joint scatter plot of two variables."""
import matplotlib.pyplot as plt

from ..data import convert_to_dataset
from .distplot import plot_dist
from .kdeplot import plot_kde
from .plot_utils import _scale_fig_size, xarray_var_iter, make_label, get_coords
from ..utils import _var_names


def plot_joint(
    data,
    var_names=None,
    coords=None,
    figsize=None,
    textsize=None,
    kind="scatter",
    gridsize="auto",
    contour=True,
    fill_last=True,
    joint_kwargs=None,
    marginal_kwargs=None,
    ax=None,
):
    """
    Plot a scatter or hexbin of two variables with their respective marginals distributions.

    Parameters
    ----------
    data : obj
        Any object that can be converted to an az.InferenceData object
        Refer to documentation of az.convert_to_dataset for details
    var_names : Iter of 2 e.g. (var_1, var_2)
        Variables to be plotted, two variables are required.
    coords : mapping, optional
        Coordinates of var_names to be plotted. Passed to `Dataset.sel`
    figsize : tuple
        Figure size. If None it will be defined automatically.
    textsize: float
        Text size scaling factor for labels, titles and lines. If None it will be autoscaled based
        on figsize.
    kind : str
        Type of plot to display (scatter, kde or hexbin)
    gridsize : int or (int, int), optional.
        The number of hexagons in the x-direction. Ignored when hexbin is False. See `plt.hexbin`
        for details
    contour : bool
        If True plot the 2D KDE using contours, otherwise plot a smooth 2D KDE. Defaults to True.
    fill_last : bool
        If True fill the last contour of the 2D KDE plot. Defaults to True.
    joint_kwargs : dicts, optional
        Additional keywords modifying the join distribution (central subplot)
    marginal_kwargs : dicts, optional
        Additional keywords modifying the marginals distributions (top and right subplot)
    ax : tuple of axes, optional
        Tuple containing (axjoin, ax_hist_x, ax_hist_y). If None, a new figure and axes
        will be created.

    Returns
    -------
    axjoin : matplotlib axes, join (central) distribution
    ax_hist_x : matplotlib axes, x (top) distribution
    ax_hist_y : matplotlib axes, y (right) distribution

    Examples
    --------
    Scatter Joint plot

    .. plot::
        :context: close-figs

        >>> import arviz as az
        >>> data = az.load_arviz_data('non_centered_eight')
        >>> az.plot_joint(data,
        >>>             var_names=['theta'],
        >>>             coords={'school': ['Choate', 'Phillips Andover']},
        >>>             kind='scatter',
        >>>             figsize=(6, 6))

    Hexbin Joint plot

    .. plot::
        :context: close-figs

        >>> az.plot_joint(data,
        >>>             var_names=['theta'],
        >>>             coords={'school': ['Choate', 'Phillips Andover']},
        >>>             kind='hexbin',
        >>>             figsize=(6, 6))

    KDE Joint plot

    .. plot::
        :context: close-figs

        >>> az.plot_joint(data,
        >>>                 var_names=['theta'],
        >>>                 coords={'school': ['Choate', 'Phillips Andover']},
        >>>                 kind='kde',
        >>>                 figsize=(6, 6))

    Overlayed plots:

    .. plot::
        :context: close-figs

        >>> data2 = az.load_arviz_data("centered_eight")
        >>> kde_kwargs = {"contourf_kwargs": {"alpha": 0}, "contour_kwargs": {"colors": "k"}}
        >>> ax = az.plot_joint(
        ...     data, var_names=("mu", "tau"), kind="kde", fill_last=False,
        ...     joint_kwargs=kde_kwargs, marginal_kwargs={"color": "k"}
        ... )
        >>> kde_kwargs["contour_kwargs"]["colors"] = "r"
        >>> az.plot_joint(
        ...     data2, var_names=("mu", "tau"), kind="kde", fill_last=False,
        ...     joint_kwargs=kde_kwargs, marginal_kwargs={"color": "r"}, ax=ax
        ... )

    """
    valid_kinds = ["scatter", "kde", "hexbin"]
    if kind not in valid_kinds:
        raise ValueError(
            ("Plot type {} not recognized." "Plot type must be in {}").format(kind, valid_kinds)
        )

    data = convert_to_dataset(data, group="posterior")

    if coords is None:
        coords = {}

    var_names = _var_names(var_names, data)

    plotters = list(xarray_var_iter(get_coords(data, coords), var_names=var_names, combined=True))

    if len(plotters) != 2:
        raise Exception(
            "Number of variables to be plotted must 2 (you supplied {})".format(len(plotters))
        )

    figsize, ax_labelsize, _, xt_labelsize, linewidth, _ = _scale_fig_size(figsize, textsize)

    if joint_kwargs is None:
        joint_kwargs = {}

    if marginal_kwargs is None:
        marginal_kwargs = {}
    marginal_kwargs.setdefault("plot_kwargs", {})
    marginal_kwargs["plot_kwargs"]["linewidth"] = linewidth

    if ax is None:
        # Instantiate figure and grid
        fig, _ = plt.subplots(0, 0, figsize=figsize, constrained_layout=True)
        grid = plt.GridSpec(4, 4, hspace=0.1, wspace=0.1, figure=fig)

        # Set up main plot
        axjoin = fig.add_subplot(grid[1:, :-1])
        # Set up top KDE
        ax_hist_x = fig.add_subplot(grid[0, :-1], sharex=axjoin)
        # Set up right KDE
        ax_hist_y = fig.add_subplot(grid[1:, -1], sharey=axjoin)
    elif len(ax) == 3:
        axjoin, ax_hist_x, ax_hist_y = ax
    else:
        raise ValueError("ax must be of lenght 3 but found {}".format(len(ax)))

    # Personalize axes
    ax_hist_x.tick_params(labelleft=False, labelbottom=False)
    ax_hist_y.tick_params(labelleft=False, labelbottom=False)

    # Set labels for axes
    x_var_name = make_label(plotters[0][0], plotters[0][1])
    y_var_name = make_label(plotters[1][0], plotters[1][1])

    axjoin.set_xlabel(x_var_name, fontsize=ax_labelsize)
    axjoin.set_ylabel(y_var_name, fontsize=ax_labelsize)
    axjoin.tick_params(labelsize=xt_labelsize)

    # Flatten data
    x = plotters[0][2].flatten()
    y = plotters[1][2].flatten()

    if kind == "scatter":
        axjoin.scatter(x, y, **joint_kwargs)
    elif kind == "kde":
        plot_kde(x, y, contour=contour, fill_last=fill_last, ax=axjoin, **joint_kwargs)
    else:
        if gridsize == "auto":
            gridsize = int(len(x) ** 0.35)
        axjoin.hexbin(x, y, mincnt=1, gridsize=gridsize, **joint_kwargs)
        axjoin.grid(False)

    for val, ax_, rotate in ((x, ax_hist_x, False), (y, ax_hist_y, True)):
        plot_dist(val, textsize=xt_labelsize, rotated=rotate, ax=ax_, **marginal_kwargs)

    ax_hist_x.set_xlim(axjoin.get_xlim())
    ax_hist_y.set_ylim(axjoin.get_ylim())

    return axjoin, ax_hist_x, ax_hist_y
