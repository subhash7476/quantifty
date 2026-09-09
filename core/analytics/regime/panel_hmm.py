"""Pooled panel Gaussian HMM — EM in log space, plus the causal forward filter.

Design: `docs/superpowers/specs/2026-09-09-n200-regime-hmm-design.md` §6, §7.

One transition matrix and one emission set are shared across every sequence, so a
state means the same thing for every name. Emissions are diagonal-covariance
Gaussians. States are sorted ascending by their first feature's emission mean
after each fit, which is what stops labels from switching across refits.

Pure numerics — no DuckDB, no file paths, no I/O. The synthetic recovery test
exercises exactly the code the folds run.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np

# Extreme rows (circuit-locked sessions, tail outliers) can drive a Gaussian
# log-density to -inf, which turns a whole sequence posterior into NaN. Flooring
# every state's log-emission equally leaves such a row uninformative — the
# posterior falls back on the transition prior instead of being destroyed.
LOG_EMISSION_FLOOR = -100.0

VAR_FLOOR = 1e-6
MIN_SEQ_LEN = 2


@dataclass(frozen=True)
class PanelHMM:
    A: np.ndarray
    pi: np.ndarray
    mu: np.ndarray
    var: np.ndarray
    order_map: tuple
    n_iter: int
    loglik: float
    converged: bool
    loglik_history: tuple = field(default=())

    @property
    def n_states(self) -> int:
        return self.A.shape[0]

    def to_dict(self) -> dict:
        return {
            "A": self.A.tolist(), "pi": self.pi.tolist(),
            "mu": self.mu.tolist(), "var": self.var.tolist(),
            "order_map": list(self.order_map), "n_iter": self.n_iter,
            "loglik": self.loglik, "converged": self.converged,
        }

    @property
    def model_hash(self) -> str:
        payload = json.dumps(
            {k: v for k, v in self.to_dict().items() if k != "n_iter"},
            sort_keys=True, separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def _logsumexp(a: np.ndarray, axis: int | None = None) -> np.ndarray:
    peak = np.max(a, axis=axis, keepdims=True)
    peak = np.where(np.isfinite(peak), peak, 0.0)
    out = peak + np.log(np.sum(np.exp(a - peak), axis=axis, keepdims=True))
    return np.squeeze(out, axis=axis) if axis is not None else out.reshape(())


def log_emissions(x: np.ndarray, mu: np.ndarray, var: np.ndarray) -> np.ndarray:
    """(T, K) log Gaussian densities with diagonal covariance, floored."""
    v = np.maximum(var, VAR_FLOOR)
    diff = x[:, None, :] - mu[None, :, :]
    quad = np.sum(diff * diff / v[None, :, :], axis=2)
    norm = np.sum(np.log(2.0 * np.pi * v), axis=1)
    return np.clip(-0.5 * (quad + norm[None, :]), LOG_EMISSION_FLOOR, None)


def _forward(log_e: np.ndarray, log_A: np.ndarray,
             log_pi: np.ndarray) -> tuple[np.ndarray, float]:
    n, k = log_e.shape
    log_alpha = np.empty((n, k))
    log_alpha[0] = log_pi + log_e[0]
    for t in range(1, n):
        log_alpha[t] = log_e[t] + _logsumexp(
            log_alpha[t - 1][:, None] + log_A, axis=0)
    return log_alpha, float(_logsumexp(log_alpha[-1]))


def _backward(log_e: np.ndarray, log_A: np.ndarray) -> np.ndarray:
    n, k = log_e.shape
    log_beta = np.zeros((n, k))
    for t in range(n - 2, -1, -1):
        log_beta[t] = _logsumexp(
            log_A + (log_e[t + 1] + log_beta[t + 1])[None, :], axis=1)
    return log_beta


def _kmeans(x: np.ndarray, k: int, seed: int, iters: int = 50) -> np.ndarray:
    """Deterministic k-means++ init, used only to seed EM.

    Hand-rolled rather than imported: the fitted artifact must be plain arrays
    with no library-version coupling, and pulling scikit-learn in for an
    initializer would reintroduce exactly that dependency.
    """
    rng = np.random.default_rng(seed)
    centers = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d2 = np.min(((x[:, None, :] - np.asarray(centers)[None, :, :]) ** 2).sum(2),
                    axis=1)
        total = d2.sum()
        probs = d2 / total if total > 0 else np.full(len(x), 1 / len(x))
        centers.append(x[rng.choice(len(x), p=probs)])
    c = np.asarray(centers)
    for _ in range(iters):
        lab = np.argmin(((x[:, None, :] - c[None, :, :]) ** 2).sum(2), axis=1)
        new = np.array([x[lab == j].mean(0) if np.any(lab == j) else c[j]
                        for j in range(k)])
        if np.allclose(new, c):
            break
        c = new
    return np.argmin(((x[:, None, :] - c[None, :, :]) ** 2).sum(2), axis=1)


def canonical_order(model: PanelHMM, sort_feature: int = 0) -> PanelHMM:
    """Sort states ascending by `sort_feature`'s emission mean (§6)."""
    perm = np.argsort(model.mu[:, sort_feature], kind="stable")
    return PanelHMM(
        A=model.A[np.ix_(perm, perm)], pi=model.pi[perm], mu=model.mu[perm],
        var=model.var[perm], order_map=tuple(int(p) for p in perm),
        n_iter=model.n_iter, loglik=model.loglik, converged=model.converged,
        loglik_history=model.loglik_history,
    )


def fit_panel(sequences: list[np.ndarray], n_states: int, seed: int = 0,
              max_iter: int = 200, tol: float = 1e-6,
              track_history: bool = False) -> PanelHMM:
    """Baum-Welch over a panel, pooling sufficient statistics across sequences."""
    seqs = [np.asarray(s, dtype=float) for s in sequences]
    if any(len(s) < MIN_SEQ_LEN for s in seqs):
        raise ValueError(f"every sequence needs at least {MIN_SEQ_LEN} rows")

    stacked = np.vstack(seqs)
    n_feat = stacked.shape[1]
    labels = _kmeans(stacked, n_states, seed)

    mu = np.array([stacked[labels == j].mean(0) if np.any(labels == j)
                   else stacked.mean(0) for j in range(n_states)])
    var = np.array([stacked[labels == j].var(0) if np.sum(labels == j) > 1
                    else stacked.var(0) for j in range(n_states)])
    var = np.maximum(var, VAR_FLOOR)
    A = np.full((n_states, n_states), 1.0 / n_states)
    pi = np.full(n_states, 1.0 / n_states)

    prev, history, converged, it = -np.inf, [], False, 0
    for it in range(1, max_iter + 1):
        num_A = np.zeros((n_states, n_states))
        sum_g = np.zeros(n_states)
        sum_gx = np.zeros((n_states, n_feat))
        sum_gxx = np.zeros((n_states, n_feat))
        pi_acc = np.zeros(n_states)
        total = 0.0

        log_A, log_pi = np.log(np.maximum(A, 1e-300)), np.log(np.maximum(pi, 1e-300))
        for s in seqs:
            log_e = log_emissions(s, mu, var)
            log_alpha, ll = _forward(log_e, log_A, log_pi)
            log_beta = _backward(log_e, log_A)
            total += ll

            gamma = np.exp(log_alpha + log_beta - ll)
            gamma /= gamma.sum(axis=1, keepdims=True)

            pi_acc += gamma[0]
            sum_g += gamma.sum(0)
            sum_gx += gamma.T @ s
            sum_gxx += gamma.T @ (s * s)

            for t in range(len(s) - 1):
                xi = (log_alpha[t][:, None] + log_A
                      + (log_e[t + 1] + log_beta[t + 1])[None, :] - ll)
                num_A += np.exp(xi)

        history.append(total)
        A = num_A / np.maximum(num_A.sum(axis=1, keepdims=True), 1e-300)
        pi = pi_acc / max(pi_acc.sum(), 1e-300)
        mu = sum_gx / np.maximum(sum_g[:, None], 1e-300)
        var = np.maximum(sum_gxx / np.maximum(sum_g[:, None], 1e-300) - mu * mu,
                         VAR_FLOOR)

        if prev > -np.inf and abs(total - prev) <= tol * max(1.0, abs(prev)):
            converged = True
            prev = total
            break
        prev = total

    model = PanelHMM(A=A, pi=pi, mu=mu, var=var, order_map=tuple(range(n_states)),
                     n_iter=it, loglik=float(prev), converged=converged,
                     loglik_history=tuple(history) if track_history else ())
    return canonical_order(model)


def filter_sequence(model: PanelHMM,
                    x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Causal filtered marginals P(S_t | F_t), entropy, and the argmax label.

    Forward recursion only. No backward pass touches this path — that is the
    property `test_filtered_probability_ignores_future_bars` pins.
    """
    x = np.asarray(x, dtype=float)
    log_e = log_emissions(x, model.mu, model.var)
    log_A = np.log(np.maximum(model.A, 1e-300))
    log_pi = np.log(np.maximum(model.pi, 1e-300))
    log_alpha, _ = _forward(log_e, log_A, log_pi)
    probs = np.exp(log_alpha - _logsumexp(log_alpha, axis=1)[:, None])
    probs /= probs.sum(axis=1, keepdims=True)
    return probs, state_entropy(probs), np.argmax(probs, axis=1)


def state_entropy(probs: np.ndarray) -> np.ndarray:
    """Shannon entropy in base K, so 0 is certainty and 1 is a uniform posterior."""
    k = probs.shape[1]
    p = np.clip(probs, 1e-300, 1.0)
    return -np.sum(p * np.log(p), axis=1) / np.log(k)


def sequence_loglik(model: PanelHMM, x: np.ndarray) -> float:
    log_e = log_emissions(np.asarray(x, dtype=float), model.mu, model.var)
    _, ll = _forward(log_e, np.log(np.maximum(model.A, 1e-300)),
                     np.log(np.maximum(model.pi, 1e-300)))
    return ll
