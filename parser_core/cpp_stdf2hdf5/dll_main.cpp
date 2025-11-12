// dllmain.cpp : ???? DLL ????????????
#include "pch.h"

BOOL APIENTRY DllMain(HMODULE hModule,
    DWORD  ul_reason_for_call,
    LPVOID lpReserved
)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}

// ??????CSV, ???????pybind11_numpy(easy) / hdf5
extern "C"  _declspec(dllexport) Cplus_stdf * NewStdf() { return new Cplus_stdf(); };
extern "C"  _declspec(dllexport) void DeleteStdf(Cplus_stdf * stdf) { stdf->Clear(); delete stdf; stdf = nullptr; };
extern "C"  _declspec(dllexport) bool ParserStdfToHdf5(Cplus_stdf * stdf, wchar_t* filename) {
    try {
        return stdf->ParserStdfToHdf5(filename);
    } catch (const std::exception& e) {
        std::cerr << "C++ Exception: " << e.what() << std::endl;
        return false;
    } catch (...) {
        std::cerr << "Unknown C++ Exception" << std::endl;
        return false;
    }
};
extern "C"  _declspec(dllexport) int GetFinishT(Cplus_stdf * stdf) { return stdf->GetFinishT(); };
