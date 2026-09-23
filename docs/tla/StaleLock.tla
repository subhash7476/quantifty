------------------------------ MODULE StaleLock ------------------------------
(***************************************************************************)
(* Stale-lock detection in scripts/ops/pidfile.py (commit e98915d).        *)
(*                                                                         *)
(* A lock file holds a PID. Holders (chain poller, EOD worker, wall        *)
(* poller, orchestrator) call acquire_lock: refuse if lock_alive, else     *)
(* write their own PID. A holder can die without releasing (Ctrl+C race,   *)
(* taskkill /F, closed console), and Windows may hand its PID to any       *)
(* unrelated process ("other" = msedge on 2026-09-21).                     *)
(*                                                                         *)
(* Mode = "mtime" : lock_alive as shipped -- PID alive AND                 *)
(*                  creation_time <= lock mtime + Tol.                     *)
(* Mode = "stamp" : proposed -- the lock also stores the writer's          *)
(*                  creation time; lock_alive requires an exact match.     *)
(*                                                                         *)
(* Atomic = FALSE : acquire is check-then-write, as shipped.               *)
(* Atomic = TRUE  : check+write is one step (O_CREAT|O_EXCL-style).        *)
(*                                                                         *)
(* One clock tick is the finest creation-time resolution; Windows cannot   *)
(* give a recycled PID a creation time at or before its previous owner's.  *)
(***************************************************************************)
EXTENDS Naturals

CONSTANTS
    Pids,      \* PIDs the OS can hand out, e.g. {1, 2}
    MaxTime,   \* clock bound for model checking
    MaxSpawns, \* bound on process starts
    Tol,       \* _START_TOLERANCE_S in ticks (only used in "mtime" mode)
    Mode,      \* "mtime" | "stamp"
    Atomic     \* BOOLEAN

ASSUME Mode \in {"mtime", "stamp"} /\ Atomic \in BOOLEAN /\ 0 \notin Pids

NoLock == [pid |-> 0, mtime |-> 0, start |-> 0, inc |-> 0]

VARIABLES
    now,      \* wall clock
    alive,    \* [Pids -> BOOLEAN]
    started,  \* [Pids -> Nat]  creation time of the process now at that PID
    inc,      \* [Pids -> Nat]  incarnation id (ghost: which process, not which PID)
    pc,       \* [Pids -> {"idle","checked","holding","done"}]
    lock,     \* lock file; .inc is a ghost recording who really wrote it
    spawns

vars == <<now, alive, started, inc, pc, lock, spawns>>

(* pidfile.lock_alive *)
LockAlive ==
    /\ lock /= NoLock
    /\ alive[lock.pid]
    /\ IF Mode = "mtime"
         THEN started[lock.pid] <= lock.mtime + Tol
         ELSE started[lock.pid] = lock.start

Init ==
    /\ now = 1
    /\ alive = [p \in Pids |-> FALSE]
    /\ started = [p \in Pids |-> 0]
    /\ inc = [p \in Pids |-> 0]
    /\ pc = [p \in Pids |-> "done"]
    /\ lock = NoLock
    /\ spawns = 0

(* The OS starts a process on a free (possibly recycled) PID.              *)
(* A holder wants the lock; an "other" process never touches it.          *)
Spawn(p, isHolder) ==
    /\ ~alive[p]
    /\ spawns < MaxSpawns
    /\ now > started[p]
    /\ alive'   = [alive   EXCEPT ![p] = TRUE]
    /\ started' = [started EXCEPT ![p] = now]
    /\ inc'     = [inc     EXCEPT ![p] = spawns + 1]
    /\ pc'      = [pc      EXCEPT ![p] = IF isHolder THEN "idle" ELSE "done"]
    /\ spawns'  = spawns + 1
    /\ UNCHANGED <<now, lock>>

Write(p) ==
    /\ lock' = [pid |-> p, mtime |-> now, start |-> started[p], inc |-> inc[p]]
    /\ pc'   = [pc EXCEPT ![p] = "holding"]

Refuse(p) ==   \* "another ... is running" -> return 1
    /\ alive' = [alive EXCEPT ![p] = FALSE]
    /\ pc'    = [pc    EXCEPT ![p] = "done"]

(* acquire_lock as shipped: read, decide, then (later) write *)
Check(p) ==
    /\ ~Atomic /\ alive[p] /\ pc[p] = "idle"
    /\ IF LockAlive
         THEN Refuse(p)
         ELSE /\ pc' = [pc EXCEPT ![p] = "checked"]
              /\ UNCHANGED alive
    /\ UNCHANGED <<now, started, inc, lock, spawns>>

WriteLock(p) ==
    /\ ~Atomic /\ alive[p] /\ pc[p] = "checked"
    /\ Write(p)
    /\ UNCHANGED <<now, alive, started, inc, spawns>>

AcquireAtomic(p) ==
    /\ Atomic /\ alive[p] /\ pc[p] = "idle"
    /\ IF LockAlive
         THEN /\ Refuse(p) /\ UNCHANGED lock
         ELSE /\ Write(p)  /\ UNCHANGED alive
    /\ UNCHANGED <<now, started, inc, spawns>>

(* Clean exit: pidfile.release_lock (compares PID only), then exit *)
Release(p) ==
    /\ alive[p] /\ pc[p] = "holding"
    /\ lock'  = IF lock.pid = p THEN NoLock ELSE lock
    /\ alive' = [alive EXCEPT ![p] = FALSE]
    /\ pc'    = [pc    EXCEPT ![p] = "done"]
    /\ UNCHANGED <<now, started, inc, spawns>>

(* TerminateProcess / taskkill /F / closed console: no cleanup runs *)
Crash(p) ==
    /\ alive[p]
    /\ alive' = [alive EXCEPT ![p] = FALSE]
    /\ pc'    = [pc    EXCEPT ![p] = "done"]
    /\ UNCHANGED <<now, started, inc, lock, spawns>>

Tick ==
    /\ now < MaxTime
    /\ now' = now + 1
    /\ UNCHANGED <<alive, started, inc, pc, lock, spawns>>

Next ==
    \/ Tick
    \/ \E p \in Pids :
         \/ Spawn(p, TRUE) \/ Spawn(p, FALSE)
         \/ Check(p) \/ WriteLock(p) \/ AcquireAtomic(p)
         \/ Release(p) \/ Crash(p)

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* The 2026-09-21 bug: lock_alive says "held", but the live process at     *)
(* that PID is not the one that wrote the lock -> it gets adopted/blocks.  *)
NoFalseAdoption == LockAlive => inc[lock.pid] = lock.inc

(* Two live processes each believe they hold the lock. *)
MutualExclusion ==
    \A p, q \in Pids :
        (alive[p] /\ alive[q] /\ pc[p] = "holding" /\ pc[q] = "holding") => p = q
=============================================================================
