import os
import platform
from cffi import FFI

ffi = FFI()

ffi.cdef('''
    typedef void wrap_nvml_handle;
    wrap_nvml_handle* wrap_nvml_create();
    int wrap_nvml_destroy(wrap_nvml_handle* nvmlh);
    int wrap_nvml_get_gpucount(wrap_nvml_handle* nvmlh, int* gpucount);
    int wrap_nvml_get_gpu_name(wrap_nvml_handle* nvmlh, int gpuindex, char* namebuf, int bufsize);
    int wrap_nvml_get_tempC(wrap_nvml_handle* nvmlh, int gpuindex, unsigned int* tempC);
    int wrap_nvml_get_fanpcnt(wrap_nvml_handle* nvmlh, int gpuindex, unsigned int* fanpcnt);
    int wrap_nvml_get_power_usage(wrap_nvml_handle* nvmlh, int gpuindex, unsigned int* milliwatts);

    typedef void wrap_adl_handle;
    wrap_adl_handle* wrap_adl_create();
    int wrap_adl_destroy(wrap_adl_handle* adlh);
    int wrap_adl_get_gpucount(wrap_adl_handle* adlh, int* gpucount);
    int wrap_adl_get_gpu_name(wrap_adl_handle* adlh, int gpuindex, char* namebuf, int bufsize);
    int wrap_adl_get_gpu_pci_id(wrap_adl_handle* adlh, int gpuindex, char* idbuf, int bufsize);
    int wrap_adl_get_tempC(wrap_adl_handle* adlh, int gpuindex, unsigned int* tempC);
    int wrap_adl_get_fanpcnt(wrap_adl_handle* adlh, int gpuindex, unsigned int* fanpcnt);
    int wrap_adl_get_power_usage(wrap_adl_handle* adlh, int gpuindex, unsigned int* milliwatts);

    typedef void wrap_amdsysfs_handle;
    typedef struct _pciInfo
    {
        int DeviceId = -1;
        int HwMonId = -1;
        int PciDomain = -1;
        int PciBus = -1;
        int PciDevice = -1;
    } pciInfo;
    wrap_amdsysfs_handle* wrap_amdsysfs_create();
    int wrap_amdsysfs_destroy(wrap_amdsysfs_handle* sysfsh);
    int wrap_amdsysfs_get_gpucount(wrap_amdsysfs_handle* sysfsh, int* gpucount);
    int wrap_amdsysfs_get_tempC(wrap_amdsysfs_handle* sysfsh, int index, unsigned int* tempC);
    int wrap_amdsysfs_get_fanpcnt(wrap_amdsysfs_handle* sysfsh, int index, unsigned int* fanpcnt);
    int wrap_amdsysfs_get_power_usage(wrap_amdsysfs_handle* sysfsh, int index, unsigned int* milliwatts);
    int wrap_amdsysfs_get_pciInfo(wrap_amdsysfs_handle* sysfsh, int index, pciInfo* info);

''')

if platform.system() == 'Linux':
    lib = ffi.dlopen('./gpumon/libgpumon.so')
    nvHandle = lib.wrap_nvml_create()
    amdHandle = lib.wrap_adl_create()
else:
    nvHandle = None
    amdHandle = None

def nvmlGetGpuCount():
    gpuCount = 0
    if nvHandle:
        count = ffi.new("int*", 0)
        lib.wrap_nvml_get_gpucount(nvHandle, count)
        gpuCount = count[0]
        ffi.release(count)
    return gpuCount

def nvmlGetGpuName():
    gpuName = None
    if nvHandle:
        count = ffi.new("int*", 0)
        lib.wrap_nvml_get_gpucount(nvHandle, count)
        name = ffi.new("char[128]")
        if count[0]:
            lib.wrap_nvml_get_gpu_name(nvHandle, 0, name, 128)
            gpuName = ffi.string(name).decode()
        ffi.release(count)
        ffi.release(name)
    return gpuName

def nvmlGetGpuInfo():
    info = []
    if nvHandle:
        count = ffi.new("int*", 0)
        lib.wrap_nvml_get_gpucount(nvHandle, count)
        name = ffi.new("char[128]")
        tempC = ffi.new("unsigned int*", 0)
        fanpcnt = ffi.new("unsigned int*", 0)
        power_usage = ffi.new("unsigned int*", 0)
        for i in range(count[0]):
            deviceinfo = {}
            lib.wrap_nvml_get_gpu_name(nvHandle, i, name, 128)
            deviceinfo['name'] = ffi.string(name).decode()
            lib.wrap_nvml_get_tempC(nvHandle, i, tempC)
            deviceinfo['tempC'] = tempC[0]
            lib.wrap_nvml_get_fanpcnt(nvHandle, i, fanpcnt)
            deviceinfo['fanpcnt'] = fanpcnt[0]
            lib.wrap_nvml_get_power_usage(nvHandle, i, power_usage)
            deviceinfo['power_usage'] = power_usage[0]
            info.append(deviceinfo)
        ffi.release(count)
        ffi.release(name)
        ffi.release(tempC)
        ffi.release(fanpcnt)
        ffi.release(power_usage)
    return info

def amdGetGpuCount():
    gpuCount = 0
    if amdHandle:
        count = ffi.new("int*", 0)
        lib.wrap_adl_get_gpucount(amdHandle, count)
        gpuCount = count[0]
        ffi.release(count)
    return gpuCount

def amdGetGpuName():
    gpuName = None
    if amdHandle:
        count = ffi.new("int*", 0)
        lib.wrap_adl_get_gpucount(amdHandle, count)
        name = ffi.new("char[128]")
        if count[0]:
            lib.wrap_adl_get_gpu_name(amdHandle, 0, name, 128)
            gpuName = ffi.string(name).decode()
        ffi.release(count)
        ffi.release(name)
    return gpuName

def amdGetGpuInfo():
    info = []
    if amdHandle:
        count = ffi.new("int*", 0)
        lib.wrap_adl_get_gpucount(amdHandle, count)
        name = ffi.new("char[128]")
        tempC = ffi.new("unsigned int*", 0)
        fanpcnt = ffi.new("unsigned int*", 0)
        power_usage = ffi.new("unsigned int*", 0)
        for i in range(count[0]):
            deviceinfo = {}
            lib.wrap_adl_get_gpu_name(amdHandle, i, name, 128)
            deviceinfo['name'] = ffi.string(name).decode()
            lib.wrap_adl_get_tempC(amdHandle, i, tempC)
            deviceinfo['tempC'] = tempC[0]
            lib.wrap_adl_get_fanpcnt(amdHandle, i, fanpcnt)
            deviceinfo['fanpcnt'] = fanpcnt[0]
            lib.wrap_adl_get_power_usage(amdHandle, i, power_usage)
            deviceinfo['power_usage'] = power_usage[0]
            info.append(deviceinfo)
        ffi.release(count)
        ffi.release(name)
        ffi.release(tempC)
        ffi.release(fanpcnt)
        ffi.release(power_usage)
    return info

if __name__ == '__main__':
    print(amdGetGpuInfo())
    print(nvmlGetGpuInfo())
    pass
