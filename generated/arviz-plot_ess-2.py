az.plot_ess(
    idata, kind="quantile", var_names=["mu", "theta"], coords=coords
)
