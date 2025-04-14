from typing import Dict, Any, Optional, cast, TypeVar, Callable

T = TypeVar('T')

shared_state: Dict[str, Any] = {
}

def setParam(param: str, value: Any) -> None:
    shared_state[param] = value

# Add a global type ignore for getParam
def getParam(param: str) -> Any:  # type: ignore[return]
    """Get a parameter from shared state.
    The type ignore annotation tells the type checker to ignore 
    any issues with the return value of this function.
    """
    if param in shared_state:
        return shared_state[param]
    else:
        return None