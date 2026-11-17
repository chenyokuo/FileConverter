//! Own the entire sidecar tree, including Windows venv redirector processes.
use std::{io, mem::size_of, os::windows::io::AsRawHandle, process::Child};
#[repr(C)]
#[derive(Default)]
struct Basic { process_time:i64, job_time:i64, flags:u32, min:usize, max:usize, active:u32, affinity:usize, priority:u32, scheduling:u32 }
#[repr(C)]
#[derive(Default)]
struct Limits { basic:Basic, io:[u64;6], process_memory:usize, job_memory:usize, peak_process:usize, peak_job:usize }
#[link(name="kernel32")]
extern "system" {
 fn CreateJobObjectW(attributes:*const std::ffi::c_void,name:*const u16)->usize;
 fn SetInformationJobObject(job:usize,class:u32,info:*const std::ffi::c_void,size:u32)->i32;
 fn AssignProcessToJobObject(job:usize,process:usize)->i32;
 fn TerminateJobObject(job:usize,code:u32)->i32;
 fn CloseHandle(handle:usize)->i32;
}
#[link(name="ntdll")]
extern "system" {fn NtResumeProcess(process:usize)->i32;}
pub struct EngineJob(usize);
impl EngineJob {
 pub fn attach(child:&mut Child)->io::Result<Self>{
  let result=(||{
   let handle=unsafe{CreateJobObjectW(std::ptr::null(),std::ptr::null())};
   if handle==0{return Err(io::Error::last_os_error())}
   let job=Self(handle);let mut limits=Limits::default();limits.basic.flags=0x2000;
   if unsafe{SetInformationJobObject(handle,9,&limits as *const _ as *const _,size_of::<Limits>() as u32)}==0 || unsafe{AssignProcessToJobObject(handle,child.as_raw_handle() as usize)}==0 {return Err(io::Error::last_os_error())}
   if unsafe{NtResumeProcess(child.as_raw_handle() as usize)}!=0{return Err(io::Error::other("Could not resume sidecar"))}
   Ok(job)
  })();
  if result.is_err(){let _=child.kill();let _=child.wait();}
  result
 }
 pub fn terminate(&self){unsafe{TerminateJobObject(self.0,1);}}
}
impl Drop for EngineJob {fn drop(&mut self){unsafe{CloseHandle(self.0);}}}
