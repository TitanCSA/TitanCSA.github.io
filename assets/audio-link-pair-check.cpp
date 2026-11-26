// C++17 read-only check for the Titan Audio Link SDK.
#include "AudioLink.h"

#include <mmdeviceapi.h>

#include <iostream>
#include <map>

int main()
{
    const auto inventory = AudioLink::List();
    if (inventory.error) {
        std::wcerr << AudioLink::Describe(inventory.error) << L'\n';
        return 1;
    }

    std::cout << "Audio inventory read. Titan endpoints: "
              << inventory.endpoints.size() << ".\n";
    unsigned active_pairs = 0;
    std::map<std::wstring, unsigned> directions;
    for (const auto& endpoint : inventory.endpoints) {
        if (!endpoint.titan || endpoint.state != DEVICE_STATE_ACTIVE || endpoint.adapter_instance.empty())
            continue;
        const unsigned direction = endpoint.direction == AudioLink::Direction::Playback ? 1u : 2u;
        auto& seen = directions[endpoint.adapter_instance];
        const bool was_paired = seen == 3u;
        seen |= direction;
        if (!was_paired && seen == 3u) ++active_pairs;
    }
    if (active_pairs)
        std::cout << "Active Titan audio pair confirmed. Adapters: " << active_pairs << ".\n";
    else if (!inventory.endpoints.empty())
        std::cout << "No active playback and recording pair on the same Titan adapter.\n";
    return 0;
}
