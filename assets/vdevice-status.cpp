// C++17 status check for Vdevice. It does not create a virtual device.
#include "Vdevice.h"

#include <iostream>

int main()
{
    const auto info = Vdevice::Get_Info();
    if (!info) {
        std::cerr << "Vdevice status unavailable (Windows " << info.error << "). ";
        if (info.error == 2) {
            std::cerr << "Run VdeviceSetup.exe from the matching demo.";
        } else {
            std::cerr << info.message;
        }
        std::cerr << '\n';
        return info.error == 2 ? 2 : 1;
    }

    std::cout << "Driver answered. Info ABI version " << info.version
              << ", device limit " << info.max_devices << '\n';
    return 0;
}
