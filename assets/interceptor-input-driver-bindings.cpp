// List the current HID keyboard and mouse drivers without changing any bindings.
#include "Interceptor.h"

#include <exception>
#include <iostream>

const wchar_t* mode_name(Interceptor::Input_Driver_Mode mode)
{
    using Interceptor::Input_Driver_Mode;
    switch (mode) {
    case Input_Driver_Mode::Windows: return L"Windows";
    case Input_Driver_Mode::Manufacturer: return L"Manufacturer";
    case Input_Driver_Mode::Interceptor: return L"Interceptor";
    case Input_Driver_Mode::Unknown: return L"Unknown";
    }
    return L"Unknown";
}

int main()
{
    try {
        const auto devices = Interceptor::Get_Input_Driver_Bindings();
        for (const auto& device : devices) {
            std::wcout << (device.mouse ? L"Mouse" : L"Keyboard")
                       << L" | " << mode_name(device.mode)
                       << L" | " << device.instance
                       << L" | service=" << device.service
                       << L" | INF=" << device.inf << L'\n';
        }
        std::wcout << L"HID input bindings: " << devices.size() << L'\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Could not list HID input drivers: " << error.what() << '\n';
        return 1;
    }
}
