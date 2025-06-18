from pydantic import BaseModel
from typing import List, Optional

class InputRequest(BaseModel):
    text: str    
    
class KeyWordRequest(BaseModel):
    keywords: List[str]

class AdvancedSearchRequest(BaseModel):
    keywords: List[str]
    language: Optional[str] = None
    min_stars: Optional[int] = None
    max_stars: Optional[int] = None
    updated_after: Optional[str] = None # Expected format YYYY-MM-DD
    exclude_forks: Optional[bool] = False

class AwesomeSearchRequest(BaseModel):
    """
    用于Awesome Agent搜索的请求模型。
    """
    domain: str