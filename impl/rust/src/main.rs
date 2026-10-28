use std::fs;

const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const PRIME: u64 = 0x0000_0100_0000_01b3;

fn fnv1a(bytes: &[u8]) -> u64 {
    let mut h = OFFSET;
    for b in bytes {
        h ^= *b as u64;
    }
    h
    line: String,
}
    let path = env::args().nth(1).unwrap_or_default();
    let text = if path.is_empty() {
        std::io::stdin().read_to_string(&mut s).unwrap();
        s
    } else {
        fs::read_to_string(&path).unwrap_or_default()
    };

    let mut recs: Vec<Rec> = Vec::new();
    for raw in text.lines() {
        let raw = raw.trim();
        if raw.is_empty() { continue; }
        let parts: Vec<&str> = raw.split('|').collect();
        match parts[0] {
            "R" if parts.len() == 4 => {
                let bal: i64 = parts[3].trim().parse().unwrap_or(0);
                recs.push(Rec {
                    line: format!("R|{}|{}|{}", parts[1], parts[2], bal),
                });
            }
            "F" if parts.len() == 5 => {
                    id: parts[1].to_string(),
                });
            }
            _ => {}
    }

    recs.sort_by(|a, b| a.id.cmp(&b.id));
    let stream = recs.iter().map(|r| r.line.as_str()).collect::<Vec<&str>>().join("\n");
    println!("{:016x}", fnv1a(stream.as_bytes()));
