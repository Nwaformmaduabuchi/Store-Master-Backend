from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def users_exception_handler(exec, context):
    res = exception_handler(exec, context)

    if res is not None:
        return Response({
            "success": False,
            "status": res.status_code,
            "error":res.data
        }, status = res.status_code)
    
    return Response(
        {
            "success": False,
            "status": 500,
            "error":["connection error, please check your network settings"]
        }, status = status.HTTP_500_INTERNAL_SERVER_ERROR
    )