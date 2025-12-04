from typing import Any

def create_unrecognized_blend(**kwargs) -> Any:
    """Model for Creating Unrecognized Blends.

    Finding objects nearby each other. Merge them into one blended
    Use Friends of Friends for matching. May implement shape matching in the future.
    Take avergaged Ra and Dec for blended source, and sum up fluxes in each band. May implement merged shapes in the future.

    The main interface method for ``Degrader``.

    Applies degradation.

    This will attach the sample to this `Degrader` (for introspection and
    provenance tracking).

    Then it will call the run() and finalize() methods, which need to be
    implemented by the sub-classes.

    The run() method will need to register the data that it creates to this
    Estimator by using ``self.add_data('output', output_data)``.

    Finally, this will return a PqHandle providing access to that output
    data.

    This function was generated from /home/tai/projects/desc-rail/alg_packages/rail_astro_tools/src/rail/creation/degraders/unrec_bl_model.py

    Parameters
    ----------
    sample : table-like
        The sample to be degraded
    seed : int, default=None
        An integer to set the numpy random seed
    output_mode: [str] default=default
        What to do with the outputs

    seed: [int] default=12345
        Random number seed

    ra_label: [str] default=ra
        ra column name

    dec_label: [str] default=dec
        dec column name

    linking_lengths: [float] default=1.0
        linking_lengths for FoF matching

    bands: list] (default=['mag_u_lsst', 'mag_g_lsst', 'mag_r_lsst', 'mag_i_lsst', 'mag_z_lsst', 'mag_y_lsst'])

    zp_dict: [dict] default={'u': 12.65, 'g': 14.69, 'r': 14.56, 'i': 14.38, 'z': 13.99, 'y': 13.02}
        magnitude zeropoints dictionary

    ref_band: str] (default=mag_i_lsst)

    redshift_col: str] (default=redshift)

    match_size: [bool] default=False
        consider object size for finding blends

    match_shape: [bool] default=False
        consider object shape for finding blends

    obj_size: [str] default=obj_size
        object size column name

    a: [str] default=semi_major
        semi major axis column name

    b: [str] default=semi_minor
        semi minor axis column name

    theta: [str] default=orientation
        orientation angle column name

    input: PqHandle (INPUT)

    output: PqHandle (OUTPUT)

    compInd: PqHandle (OUTPUT)

    Returns
    -------
    output_data : PqHandle
        A handle giving access to a table with degraded sample"""
