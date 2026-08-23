# curveprotocol

Reference engine for the Exponential Curve Protocol. Reserves hold USDT in
bands, a curve compounds them toward a ceiling, and depth scoring reports how
much of the book survives a draw.

No floats. Balances are integer micro-USDT, so a projection made on one machine
is byte-identical to the same projection on another, in every port.

## Model

Five bands, drained in order:

| band   | weight | role             |
| ------ | ------ | ---------------- |
| seed   | 1.00   | bootstrap        |
| core   | 1.00   | standing reserve |
| buffer | 0.80   | first draw       |
| edge   | 0.45   | opportunistic    |
| sink   | 0.20   | last resort      |

A reserve is a tranche. A flow moves value between tranches. Flows form a DAG
and cycles are rejected at assembly time.
