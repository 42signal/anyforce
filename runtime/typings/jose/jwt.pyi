from typing import Any, Dict, List, Optional, Union

def encode(
    claims: Dict[str, Any],
    key: str,
    algorithm: Optional[str] = ...,
    headers: Optional[Dict[str, str]] = ...,
    access_token: Optional[str] = ...,
) -> str: ...
def decode(
    token: str,
    key: str,
    algorithms: Optional[Union[List[str], str]] = ...,
    options: Optional[Dict[str, Any]] = ...,
    audience: Optional[str] = ...,
    issuer: Optional[Union[List[str], str]] = ...,
    subject: Optional[str] = ...,
    access_token: Optional[str] = ...,
) -> Dict[str, str]: ...
