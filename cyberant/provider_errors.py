"""Safe provider diagnostics: never log exception text, requests or response bodies."""
import json,logging,re,secrets
import httpx
from fastapi import HTTPException
from cyberant import model_provider

LOGGER=logging.getLogger('cyberant.provider')

def failure(error,model,stage,usage_id,elapsed):
    status=None;code=503
    if isinstance(error,model_provider.InvalidCompletion):
        kind='empty_content' if error.reason=='empty_content' else 'invalid_response'
        message='Model không trả nội dung hợp lệ; usage đã được ghi nhận nếu có.'
    elif isinstance(error,httpx.HTTPStatusError):
        kind='http_status';status=error.response.status_code
        message={401:'API key không hợp lệ.',402:'OpenRouter không đủ số dư.',429:'Nhà cung cấp đang giới hạn lượt gọi.'}.get(status,'Model hoặc web từ chối yêu cầu.')
    elif isinstance(error,httpx.TimeoutException):
        kind='http_timeout';code=504
        message='Hết thời gian chờ phản hồi từ OpenRouter.'
    elif isinstance(error,TimeoutError):
        kind='deadline_exceeded';code=504
        message='Đã hết thời gian xử lý tổng.'
    elif isinstance(error,httpx.ConnectError):
        kind='connection_error'
        message='Không kết nối được tới OpenRouter; cần kiểm tra DNS, TLS và mạng outbound của server.'
    elif isinstance(error,httpx.HTTPError):
        kind='transport_error'
        message='Kết nối với OpenRouter bị lỗi khi gửi hoặc nhận phản hồi.'
    elif isinstance(error,json.JSONDecodeError):
        kind='invalid_json'
        message='OpenRouter trả phản hồi không đọc được thành JSON.'
    else:
        kind='invalid_response'
        message='Phản hồi OpenRouter không đúng định dạng mong đợi.'
    reference=secrets.token_hex(8)
    # Model is server config, but restrict characters/length to prevent log injection.
    safe_model=model if isinstance(model,str) and re.fullmatch(r'[A-Za-z0-9_./:+-]{1,200}',model) else 'invalid_model_id'
    record=dict(event='provider_failure',error_id=reference,kind=kind,
                exception_type=type(error).__name__ if type(error).__module__ in ('httpx','builtins','json.decoder','cyberant.model_provider') else 'ProviderError',
                model=safe_model,stage=stage,usage_record_id=usage_id,elapsed_seconds=round(elapsed,2),http_status=status)
    detail=json.dumps(record,ensure_ascii=True,separators=(',',':'))
    LOGGER.warning('%s',detail)
    message+=' Không tự gọi lại; kiểm tra usage trước khi gửi lại. Mã lỗi: '+reference+'.'
    return HTTPException(code,message),detail