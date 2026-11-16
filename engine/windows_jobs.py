"""Windows child-process lifetime management; nested jobs supported on Windows 10/11."""
import os
import ctypes

def prevent_orphans(process_handle=None):
    """Windows job kills all descendants if service dies or desktop closes."""
    if os.name != 'nt': return
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('ProcessTime',ctypes.c_int64),('JobTime',ctypes.c_int64),('LimitFlags',w.DWORD),('Min',ctypes.c_size_t),('Max',ctypes.c_size_t),('Active',w.DWORD),('Affinity',ctypes.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]
    class Io(ctypes.Structure):
        _fields_ = [(n,ctypes.c_uint64) for n in ['ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes']]
    class Limits(ctypes.Structure):
        _fields_ = [('Basic',Basic),('Io',Io),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcess',ctypes.c_size_t),('PeakJob',ctypes.c_size_t)]
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.CreateJobObjectW.restype=w.HANDLE
    k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
    k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
    k.GetCurrentProcess.restype=w.HANDLE
    handle=k.CreateJobObjectW(None,None)
    limits=Limits();limits.Basic.LimitFlags=0x2000
    if not handle or not k.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(handle,process_handle or k.GetCurrentProcess()):
        raise RuntimeError('Windows Job Object 初始化失敗，無法保證程序清理')
    return handle  # intentionally held for lifetime of service

