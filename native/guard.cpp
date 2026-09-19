// Independent implementation of the reduced arithmetic guard, not a hardware PLC.
// stdin: external internal offset uncertainty_external uncertainty_internal
//        uncertainty_offset policy (seconds). One case per line.
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::array<long double, 7> v{};
        bool valid = true;
        for (auto &x : v) {
            if (!(input >> x) || !std::isfinite(x) || std::abs(x) > 1e15L) valid = false;
        }
        std::string extra;
        if (input >> extra) valid = false;
        for (auto i : {0,1,3,4,5,6}) if (v[i] < 0) valid = false;
        if (!valid) {
            std::cout << "{\"status\":\"INVALID\",\"action\":\"LOCKOUT\"}\n";
            continue;
        }
        const long double raw = v[0]+v[1]-std::abs(v[2]);
        const long double safe = raw-v[3]-v[4]-v[5]-v[6];
        // Conservative floating arithmetic guard; scale-aware rounding region closes.
        const long double eps = 1e-15L*std::max({1.0L,std::abs(v[0]),std::abs(v[1]),std::abs(v[2])});
        const char *status = raw < 0 ? "FAIL" : safe <= eps ? "CRITICAL" : "PASS";
        const char *action = raw < 0 ? "LOCKOUT" : safe <= eps ? "CLOSE" : "ALLOW_ANALOG";
        std::cout << std::setprecision(17) << "{\"status\":\"" << status
                  << "\",\"action\":\"" << action << "\",\"safe_margin_s\":" << safe << "}\n";
    }
}
