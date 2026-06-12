"""
External stamp request model — matches the JSON format from calling systems.

Example:
{
    "requestNo": "VP202606040001",
    "businessId": "VP-BIZ-20260604-0001",
    "systemCode": "VP",
    "systemName": "VP系统",
    "contractName": "采购合同-测试.pdf",
    "fileUrl": "https://vp.example.com/file/contract/xxx.pdf",
    "fileType": "pdf",
    "sealType": "OFFICIAL",
    "sealCode": "VP_GZ_001",
    "sealReason": "VP流程审批通过，发起自动盖章",
    "pageNo": 1,
    "position": {"x": 420, "y": 680, "width": 120, "height": 120},
    "operator": {"userId": "zhangsan", "userName": "张三", "mobile": "13800138000"},
    "callbackUrl": "https://vp.example.com/api/seal/callback",
    "remark": "VP调用外部盖章系统示例"
}
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class Position(BaseModel):
    """Stamp position on the page. Units: points (pt) at 72 DPI."""
    x: float = Field(..., description="X coordinate from left (pt)")
    y: float = Field(..., description="Y coordinate from bottom (pt)")
    width: float = Field(..., description="Seal display width (pt)")
    height: float = Field(..., description="Seal display height (pt)")


class Operator(BaseModel):
    """Operator / submitter info."""
    userId: str = Field(..., description="User ID")
    userName: str = Field("", description="User name")
    mobile: str = Field("", description="Mobile number")


class FileType(str, Enum):
    PDF = "pdf"
    DWG = "dwg"


class StampRequest(BaseModel):
    """Incoming stamp request from an external system."""
    requestNo: str = Field(..., min_length=1, max_length=64, description="请求编号")
    businessId: str = Field("", description="业务ID")
    systemCode: str = Field("", description="调用系统代码")
    systemName: str = Field("", description="调用系统名称")
    contractName: str = Field("", description="文件名称")
    fileUrl: str = Field(..., description="文件下载地址")
    fileType: FileType = Field(..., description="文件类型: pdf / dwg")
    sealType: str = Field("OFFICIAL", description="印章类型")
    sealCode: str = Field(..., description="印章业务编码")
    sealReason: str = Field("", description="盖章原因")
    pageNo: int = Field(1, ge=1, description="页码")
    position: Position = Field(..., description="盖章坐标和尺寸")
    operator: Optional[Operator] = Field(None, description="操作人信息")
    callbackUrl: Optional[str] = Field(None, description="回调地址（异步通知结果）")
    remark: str = Field("", description="备注")


class StampResponse(BaseModel):
    """Immediate response after accepting a stamp request."""
    requestNo: str
    status: str = "ACCEPTED"  # ACCEPTED / PROCESSING / SUCCESS / FAILED
    message: str = "请求已接收，正在处理"


class CallbackPayload(BaseModel):
    """Payload sent to callbackUrl when stamping completes."""
    requestNo: str
    businessId: str = ""
    status: str  # SUCCESS / FAILED
    message: str = ""
    fileUrl: Optional[str] = None  # Stamped file download URL
    fileType: Optional[str] = None
    stampedFileName: Optional[str] = None
    errorDetail: Optional[str] = None
