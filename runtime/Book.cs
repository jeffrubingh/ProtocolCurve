using System.Security.Cryptography;
using System.Text;

namespace CurveProtocol.Runtime;

/// <summary>
/// The assembled book. Built once, then read-only. The digest depends only on
/// ids, bands, balances and flow edges, so the same logical book always yields
/// the same value.
/// </summary>
public sealed class Book
{
    private readonly Dictionary<string, ReserveRecord> _reserves;
    private readonly Dictionary<string, FlowRecord> _flows;
    private readonly Dictionary<string, List<string>> _producers;
    private readonly Dictionary<string, List<string>> _consumers;

    private Book(
        Dictionary<string, ReserveRecord> reserves,
        Dictionary<string, FlowRecord> flows,
        Dictionary<string, List<string>> producers,
        Dictionary<string, List<string>> consumers)
    {
        _reserves = reserves;
        _flows = flows;
        _producers = producers;
        _consumers = consumers;
    }

    public IReadOnlyDictionary<string, ReserveRecord> Reserves => _reserves;
    public IReadOnlyDictionary<string, FlowRecord> Flows => _flows;

    public static Book Build(BookDocument document, bool strict = true)
    {
        var reserves = new Dictionary<string, ReserveRecord>(StringComparer.Ordinal);
        foreach (var reserve in document.Reserves)
        {
            if (string.IsNullOrEmpty(reserve.Id))
                throw new BookException("reserve record is missing required field 'id'");
            if (reserves.ContainsKey(reserve.Id))
                throw new BookException($"duplicate reserve id: {reserve.Id}");
            reserves[reserve.Id] = reserve;
        }

        var flows = new Dictionary<string, FlowRecord>(StringComparer.Ordinal);
        var producers = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var consumers = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        foreach (var flow in document.Flows)
        {
            if (string.IsNullOrEmpty(flow.Id))
                throw new BookException("flow record is missing required field 'id'");
            if (flows.ContainsKey(flow.Id))
                throw new BookException($"duplicate flow id: {flow.Id}");
            if (strict && flow.Outputs.Count == 0)
                throw new BookException($"flow {flow.Id} credits nothing");
            flows[flow.Id] = flow;

            foreach (var id in flow.Inputs)
            {
                if (!reserves.ContainsKey(id))
                {
                    if (strict) throw new BookException($"flow {flow.Id} debits unknown reserve {id}");
                    reserves[id] = new ReserveRecord { Id = id };
                }
                if (!consumers.TryGetValue(id, out var list)) consumers[id] = list = new();
                list.Add(flow.Id);
            }

            foreach (var id in flow.Outputs)
            {
                if (!reserves.ContainsKey(id))
                {
                    if (strict) throw new BookException($"flow {flow.Id} credits unknown reserve {id}");
                    reserves[id] = new ReserveRecord { Id = id };
                }
                if (!producers.TryGetValue(id, out var list)) producers[id] = list = new();
                list.Add(flow.Id);
            }
        }

        var book = new Book(reserves, flows, producers, consumers);
        book.RejectCycles();
        return book;
    }

    public IEnumerable<string> ReserveIds() => _reserves.Keys.OrderBy(k => k, StringComparer.Ordinal);

    public IEnumerable<string> FlowIds() => _flows.Keys.OrderBy(k => k, StringComparer.Ordinal);

    /// <summary>Reserves nothing debits; a flow with no inputs starts a branch.</summary>
    public IReadOnlyList<string> Origins() =>
        ReserveIds()
            .Where(id => !_producers.TryGetValue(id, out var ps) || ps.All(f => _flows[f].Inputs.Count == 0))
            .ToList();

    /// <summary>Reserves nothing credits.</summary>
    public IReadOnlyList<string> Terminals() =>
        ReserveIds().Where(id => !_consumers.ContainsKey(id)).ToList();

    /// <summary>Ordered ancestry of one tranche, ancestors before descendants.</summary>
    public List<string> Ancestry(string reserveId)
    {
        if (!_reserves.ContainsKey(reserveId))
            throw new BookException($"unknown reserve: {reserveId}");

        var seen = new HashSet<string>(StringComparer.Ordinal);
        var order = new List<string>();

        void Walk(string node)
        {
            if (!_producers.TryGetValue(node, out var ps)) return;
            foreach (var flowId in ps)
            {
                foreach (var parent in _flows[flowId].Inputs.OrderBy(p => p, StringComparer.Ordinal))
                {
                    if (!seen.Add(parent)) continue;
                    Walk(parent);
                    order.Add(parent);
                }
            }
        }

        Walk(reserveId);
        return order;
    }

    public string Digest()
    {
        var builder = new StringBuilder();
        foreach (var id in ReserveIds())
        {
            var reserve = _reserves[id];
            builder.Append($"R|{reserve.Id}|{reserve.NormalisedBand}|{reserve.Balance}\n");
        }
        foreach (var id in FlowIds())
        {
            var flow = _flows[id];
            var inputs = string.Join(",", flow.Inputs.OrderBy(i => i, StringComparer.Ordinal));
            var outputs = string.Join(",", flow.Outputs.OrderBy(o => o, StringComparer.Ordinal));
            builder.Append($"F|{flow.Id}|{flow.Op}|{inputs}|{outputs}\n");
        }
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(builder.ToString()));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    private void RejectCycles()
    {
        var state = new Dictionary<string, int>(StringComparer.Ordinal);

        IEnumerable<string> Sinks(string node) =>
            _consumers.TryGetValue(node, out var fs)
                ? fs.SelectMany(f => _flows[f].Outputs).Distinct().OrderBy(s => s, StringComparer.Ordinal)
                : Enumerable.Empty<string>();

        foreach (var start in ReserveIds())
        {
            if (state.ContainsKey(start)) continue;
            var stack = new Stack<(string Node, IEnumerator<string> Children)>();
            state[start] = 1;
            stack.Push((start, Sinks(start).GetEnumerator()));
            while (stack.Count > 0)
            {
                var (node, children) = stack.Peek();
                if (children.MoveNext())
                {
                    var child = children.Current;
                    if (state.TryGetValue(child, out var colour) && colour == 1)
                        throw new BookException($"cycle through reserve {child}");
                    if (!state.ContainsKey(child))
                    {
                        state[child] = 1;
                        stack.Push((child, Sinks(child).GetEnumerator()));
                    }
                }
                else
                {
                    state[node] = 2;
                    stack.Pop();
                }
            }
        }
    }
}
