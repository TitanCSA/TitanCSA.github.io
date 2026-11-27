#include "Vdevice.h"

#include <iostream>
#include <string_view>

namespace {
Vdevice::Device_Config fixture_config()
{
    Vdevice::Descriptor device;
    device.data = {18, 1, 0, 2, 0, 0, 0, 64, 0xff, 0xff, 0x11, 0, 0, 1, 0, 0, 0, 1};

    Vdevice::Descriptor report;
    report.kind = Vdevice::Descriptor_Kind::Report;
    report.data = {
        0x06, 0x00, 0xff, 0x09, 0x01, 0xa1, 0x01,
        0x15, 0x00, 0x26, 0xff, 0x00, 0x75, 0x08, 0x95, 0x10, 0x09, 0x02, 0x81, 0x02, 0xc0
    };

    Vdevice::Descriptor configuration;
    configuration.data = {
        9, 2, 34, 0, 1, 1, 0, 0x80, 50,
        9, 4, 0, 0, 1, 3, 0, 0, 0,
        9, 0x21, 0x11, 1, 0, 1, 0x22, static_cast<std::uint8_t>(report.data.size()), 0,
        7, 5, 0x81, 3, 16, 0, 8
    };

    Vdevice::Device_Config config;
    config.descriptors = {device, configuration, report};
    return config;
}

void print_info(const Vdevice::Info& info)
{
    std::cout << "{\"error\":" << info.error
              << ",\"abi\":" << info.version
              << ",\"trial_started\":" << info.trial_started
              << ",\"trial_expired\":" << info.trial_expired
              << ",\"remaining_100ns\":" << info.trial_remaining_100ns
              << ",\"session_devices\":" << info.devices.size() << "}";
}
}

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "Use status, cycle or validate.\n";
        return 64;
    }
    const std::string_view mode(argv[1]);
    std::cout << std::boolalpha;
    if (mode == "status") {
        const auto info = Vdevice::Get_Info();
        print_info(info);
        std::cout << '\n';
        return 0;
    }
    const auto config = fixture_config();
    const auto validation = Vdevice::Validate_Device(config);
    if (mode == "validate") {
        std::cout << "{\"validation_error\":" << validation.error << "}\n";
        return validation ? 0 : 1;
    }
    if (mode != "cycle" || !validation) {
        std::cerr << "Fixture or command invalid.\n";
        return 64;
    }
    const auto before = Vdevice::Get_Info();
    auto fixture = Vdevice::Create_Device(config);
    const auto after = Vdevice::Get_Info();
    const auto ready_error = fixture ? Vdevice::Wait_Device_Ready(fixture, 10000).error : fixture.error;
    const auto close_error = fixture ? Vdevice::Delete_Device(fixture).error : fixture.error;
    std::cout << "{\"before\":";
    print_info(before);
    std::cout << ",\"after_create\":";
    print_info(after);
    std::cout << ",\"create_error\":" << fixture.error << ",\"ready_error\":" << ready_error
              << ",\"close_error\":" << close_error << ",\"after_close\":";
    print_info(Vdevice::Get_Info());
    std::cout << "}\n";
    return 0;
}
