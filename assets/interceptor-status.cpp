// C++17 status check for one installed Interceptor edition.
#include "Interceptor.h"

#include <iostream>
#include <system_error>

int main()
{
    try {
        // The published SDK exposes this without starting a capture session.
        const auto status = Interceptor::Get_Status();
        std::cout << "Driver answered. Status ABI version " << status.version << '\n';
        return 0;
    } catch (const std::system_error& error) {
        std::cerr << "Driver status unavailable (Windows " << error.code().value() << "). "
                  << "Use the installer for your Interceptor edition.\n";
        return error.code().value() == ERROR_FILE_NOT_FOUND ? 2 : 1;
    }
}
