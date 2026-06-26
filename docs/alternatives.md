# Related Projects

Last checked: 2026-06-26.

ACO overlaps with several mature open-source categories:

| Project | Stars Checked | Main Fit | Notes |
| --- | ---: | --- | --- |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 51k+ | AI gateway, proxy, load balancing, cost tracking | Strongest replacement candidate for unified provider access. |
| [QuantumNous/new-api](https://github.com/QuantumNous/new-api) | 40k+ | Unified model hub and API distribution | Strong replacement candidate for relay/key distribution. |
| [songquanpeng/one-api](https://github.com/songquanpeng/one-api) | 35k+ | LLM API management and redistribution | Strong replacement candidate for admin/key/channel management. |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 29k+ | Observability, metrics, prompts, evals | Better to integrate than rebuild observability. |
| [tensorzero/tensorzero](https://github.com/tensorzero/tensorzero) | 11k+ | Gateway, observability, evals, optimization | Broad LLMOps platform, heavier than ACO. |
| [coaidev/coai](https://github.com/coaidev/coai) | 9k+ | Multi-tenant gateway, billing, cost management | Strong SaaS-style gateway alternative. |
| [katanemo/plano](https://github.com/katanemo/plano) | 6k+ | Agentic proxy, observability, smart routing | Good reference for agent-focused routing. |
| [maximhq/bifrost](https://github.com/maximhq/bifrost) | 6k+ | High-performance AI gateway | Strong gateway/runtime reference. |
| [Helicone/helicone](https://github.com/Helicone/helicone) | 5k+ | LLM observability | Better to integrate than rebuild analytics. |
| [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | 5k+ | LLM routing and cost-quality tradeoff | Useful algorithmic reference for routing. |

## Product Conclusion

These projects already cover gateway execution, key distribution, quota enforcement, billing, spend tracking, load balancing, and observability. They do not appear to provide a complete layer for future quota-waste prediction, idle-capacity detection, and optimization recommendations.

Current recommendation: do not compete head-on as another generic LLM gateway. Keep ACO focused on quota forecasting, idle-capacity prediction, personal/local usage optimization, and integration with existing gateways such as LiteLLM, New API, one-api, Langfuse, or Helicone.

ACO's differentiated role:

- Import usage, quota, budget, and spend data from mature gateways.
- Predict month-end usage, waste, and overrun risk.
- Identify idle capacity before it expires.
- Recommend useful work that can consume otherwise wasted capacity.
- Leave provider routing, key distribution, billing, and production proxying to mature gateway projects.
