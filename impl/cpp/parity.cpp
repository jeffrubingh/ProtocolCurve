// Parity checker for the canonical book format.
//
// Reads R|id|band|balance and F|id|op|inputs|outputs lines, validates the
// references, and prints the weighted depth with the FNV-1a 64 fingerprint
// every other port must agree on.

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace {

constexpr std::int64_t kMicro = 1'000'000;
constexpr std::int64_t kFloor = 250 * kMicro;
constexpr std::uint64_t kFnvOffset = 0xCBF29CE484222325ULL;
constexpr std::uint64_t kFnvPrime = 0x100000001B3ULL;

struct Reserve {
    std::string id;
    std::string band;
    std::int64_t balance = 0;
};

struct Flow {
    std::string id;
    std::string op;
    std::vector<std::string> inputs;
    std::vector<std::string> outputs;
};

std::int64_t weight_micro(const std::string& band) {
    if (band == "buffer") return 800'000;
    if (band == "edge") return 450'000;
    if (band == "sink") return 200'000;
    return kMicro;
}

std::string normalise_band(const std::string& band) {
    if (band == "seed" || band == "core" || band == "buffer" || band == "edge" || band == "sink") {
        return band;
    }
    return "core";
}

std::vector<std::string> split_list(const std::string& field) {
    std::vector<std::string> parts;
    std::string current;
    for (char c : field) {
        if (c == ',') {
            if (!current.empty()) parts.push_back(current);
            current.clear();
        } else {
            current.push_back(c);
        }
    }
    if (!current.empty()) parts.push_back(current);
    return parts;
}

bool parse(const std::string& text, std::map<std::string, Reserve>& reserves,
           std::map<std::string, Flow>& flows, std::string& error) {
    std::istringstream stream(text);
    std::string line;
    int number = 0;

    while (std::getline(stream, line)) {
        ++number;
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        if (line.empty() || line[0] == '#') continue;

        std::vector<std::string> fields;
        std::string current;
        for (char c : line) {
            if (c == '|') {
                fields.push_back(current);
                current.clear();
            } else {
                current.push_back(c);
            }
        }
        fields.push_back(current);

        if (fields[0] == "R") {
            if (fields.size() != 4) { error = "line " + std::to_string(number) + ": reserve needs 4 fields"; return false; }
            if (reserves.count(fields[1])) { error = "line " + std::to_string(number) + ": duplicate reserve " + fields[1]; return false; }
            Reserve reserve;
            reserve.id = fields[1];
            reserve.band = normalise_band(fields[2]);
            try {
                reserve.balance = std::stoll(fields[3]);
            } catch (...) {
                error = "line " + std::to_string(number) + ": bad balance";
                return false;
            }
            reserves[reserve.id] = reserve;
        } else if (fields[0] == "F") {
            if (fields.size() != 5) { error = "line " + std::to_string(number) + ": flow needs 5 fields"; return false; }
            if (flows.count(fields[1])) { error = "line " + std::to_string(number) + ": duplicate flow " + fields[1]; return false; }
            Flow flow;
            flow.id = fields[1];
            flow.op = fields[2].empty() ? "derive" : fields[2];
            flow.inputs = split_list(fields[3]);
            flow.outputs = split_list(fields[4]);
            if (flow.outputs.empty()) { error = "line " + std::to_string(number) + ": flow " + flow.id + " credits nothing"; return false; }
            flows[flow.id] = flow;
        } else {
            error = "line " + std::to_string(number) + ": unknown record " + fields[0];
            return false;
        }
    }

    for (const auto& [id, flow] : flows) {
        for (const auto& ref : flow.inputs) {
            if (!reserves.count(ref)) { error = "flow " + id + ": unknown reserve " + ref; return false; }
        }
        for (const auto& ref : flow.outputs) {
            if (!reserves.count(ref)) { error = "flow " + id + ": unknown reserve " + ref; return false; }
        }
    }
    return true;
}

std::string fingerprint(const std::map<std::string, Reserve>& reserves,
                        const std::map<std::string, Flow>& flows) {
    std::ostringstream payload;
    for (const auto& [id, reserve] : reserves) {
        payload << "R|" << reserve.id << '|' << reserve.band << '|' << reserve.balance << '\n';
    }
    for (const auto& [id, flow] : flows) {
        std::set<std::string> ins(flow.inputs.begin(), flow.inputs.end());
        std::set<std::string> outs(flow.outputs.begin(), flow.outputs.end());
        payload << "F|" << flow.id << '|' << flow.op << '|';
        bool first = true;
        for (const auto& in : ins) { if (!first) payload << ','; payload << in; first = false; }
        payload << '|';
        first = true;
        for (const auto& out : outs) { if (!first) payload << ','; payload << out; first = false; }
        payload << '\n';
    }

    const std::string text = payload.str();
    std::uint64_t hash = kFnvOffset;
    for (unsigned char byte : text) {
        hash ^= byte;
        hash *= kFnvPrime;
    }

    std::ostringstream hex;
    hex << std::hex << std::setw(16) << std::setfill('0') << hash;
    return hex.str();
}

int self_test() {
    const std::string book = "R|a|seed|1000000\nR|b|core|500000\nF|f|deposit|a|b\n";
    std::map<std::string, Reserve> reserves;
    std::map<std::string, Flow> flows;
    std::string error;
    if (!parse(book, reserves, flows, error)) { std::cerr << "self-test parse: " << error << '\n'; return 1; }
    if (reserves.size() != 2 || flows.size() != 1) { std::cerr << "self-test counts\n"; return 1; }
    if (fingerprint(reserves, flows).size() != 16) { std::cerr << "self-test width\n"; return 1; }

    std::map<std::string, Reserve> r2;
    std::map<std::string, Flow> f2;
    if (parse("R|a|core|1\nF|f|deposit|a|ghost\n", r2, f2, error)) { std::cerr << "self-test unknown ref\n"; return 1; }
    if (parse("R|a|core|1\nF|f|deposit|a|\n", r2, f2, error)) { std::cerr << "self-test empty outputs\n"; return 1; }

    std::cout << "self-test ok\n";
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: parity <book.txt> | --self-test\n";
        return 2;
    }
    const std::string path = argv[1];
    if (path == "--self-test") return self_test();

    std::ifstream file(path);
    if (!file) { std::cerr << "error: cannot open " << path << '\n'; return 1; }
    std::ostringstream buffer;
    buffer << file.rdbuf();

    std::map<std::string, Reserve> reserves;
    std::map<std::string, Flow> flows;
    std::string error;
    if (!parse(buffer.str(), reserves, flows, error)) { std::cerr << "error: " << error << '\n'; return 3; }

    std::int64_t raw = 0;
    std::int64_t depth = 0;
    int thin = 0;
    for (const auto& [id, reserve] : reserves) {
        raw += reserve.balance;
        depth += reserve.balance * weight_micro(reserve.band) / kMicro;
        if (reserve.balance > 0 && reserve.balance < kFloor) ++thin;
    }

    std::set<std::string> debited;
    for (const auto& [id, flow] : flows) {
        if (flow.inputs.empty()) continue;
        for (const auto& out : flow.outputs) debited.insert(out);
    }
    std::vector<std::string> origins;
    for (const auto& [id, reserve] : reserves) {
        if (!debited.count(id)) origins.push_back(id);
    }

    const double score = raw > 0 ? static_cast<double>(depth) / static_cast<double>(raw) : 0.0;

    std::cout << "reserves " << reserves.size() << '\n';
    std::cout << "flows " << flows.size() << '\n';
    std::cout << "raw " << raw << '\n';
    std::cout << "depth " << depth << '\n';
    std::cout << "score " << std::fixed << std::setprecision(4) << score << '\n';
    std::cout << "thin " << thin << '\n';
    std::cout << "origins ";
    for (std::size_t i = 0; i < origins.size(); ++i) { if (i) std::cout << ','; std::cout << origins[i]; }
    std::cout << '\n';
    std::cout << "fingerprint " << fingerprint(reserves, flows) << '\n';
    return 0;
}
