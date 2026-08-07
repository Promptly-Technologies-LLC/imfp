from os import environ
from warnings import warn

import type_enforced


@type_enforced.Enforcer
def set_imf_app_name(name: str = "imfp") -> None:
    """
    Set the IMF Application Name.

    Set a unique application name to be used in requests to the IMF API as an
    environment variable.

    Args:
        name (str, optional): A string representing the application name.
        Default is "imfp".

    Returns:
        None

    Raises:
        ValueError: If the provided name is not a valid string or contains
        forbidden characters.

    Examples:
        imf_app_name("my_custom_app_name")
    """

    if len(name) > 255:
        raise ValueError("Application name must be no longer than 255 characters.")

    if name == "imfp" or name == "":
        warn(
            "Best practice is to choose a unique app name. Use of a default "
            "or empty app name may result in hitting API rate limits and "
            "being blocked by the API.",
            UserWarning,
        )

    forbidden_chars = set(range(32)) | {127}
    if any(ord(c) in forbidden_chars for c in name):
        raise ValueError(
            "The application name contains forbidden characters. "
            "Please remove control characters and non-printable "
            "ASCII characters."
        )

    environ["IMF_APP_NAME"] = name

    return None


@type_enforced.Enforcer
def set_imf_wait_time(wait_time: int | float = 1.5) -> None:
    """
    Set the IMF wait time as an environment variable.

    Args:
        wait_time (Union[int, float], optional): The wait time in seconds to be set as an environment variable. Defaults to 1.5.

    Raises:
        TypeError: If the provided wait_time is not a numeric value (int or float).
        ValueError: If the provided wait_time is not greater than 0.
    """
    if wait_time >= 0:
        environ["IMF_WAIT_TIME"] = str(wait_time)
    else:
        raise ValueError("Rate limit wait time must be greater than or equal to 0.")
