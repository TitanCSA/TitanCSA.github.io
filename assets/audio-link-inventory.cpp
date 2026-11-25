// C++17 read-only check for the Titan Audio Link SDK.
#include "AudioLink.h"

#include <iostream>

int main()
{
    const auto inventory = AudioLink::List();
    if (inventory.error) {
        std::wcerr << AudioLink::Describe(inventory.error) << L'\n';
        return 1;
    }

    std::cout << "Audio inventory read. Titan endpoints: "
              << inventory.endpoints.size() << ".\n";
    return 0;
}
