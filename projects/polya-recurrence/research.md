# Pólya's recurrence theorem: research notes

Idealised model: a walker on the integer lattice Z^d starts at the origin ("home") and at each step moves to one of its 2d lattice neighbours chosen uniformly and independently.

## Result (Pólya, 1921)
- d = 1, 2: **recurrent**. P(return to origin) = 1, and the walker returns infinitely often with probability 1.
- d >= 3: **transient**. P(return) = p(d) < 1; the walker returns only finitely many times and escapes with probability 1 - p(d).

| d | p(d), P(ever returns) | Source / check |
|---|---|---|
| 1 | 1 | recurrent |
| 2 | 1 | recurrent |
| 3 | 0.3405373 | Watson integral G(3) = 1.5163861; p = 1 - 1/G (recomputed here with SciPy and the closed-form Gamma expression, both agree) |
| 4 | 0.1932017 | same integral, recomputed |
| 5 | 0.1351786 | same integral, recomputed |

## Why (the video's argument)
Let u_2n = P(S_2n = 0). The expected number of returns is the sum over n >= 1 of u_2n.
- d = 2: u_2n = [C(2n,n)/4^n]^2 ~ 1/(pi n). The sum diverges (harmonic series), so the walk is recurrent.
- d = 3: u_2n ~ 2 (3/(4 pi n))^(3/2). The sum converges to G(3) - 1 = 0.5164, so returns are finite in number.
- Checked numerically: exact u_2n for n up to 300 agrees with the asymptotics to under 0.2%; cumulative sums at n = 300 are 1.883 (2D, still growing like ln n / pi) and 0.489 (3D, limit 0.516).

## Things the video must not claim
- The bird is not certainly lost: it returns with probability about 0.34.
- The man does not get home quickly: the expected return time is infinite in 1D and 2D.
- This is a model of unbiased lattice walks, not of real animals.
- The Kakutani line is a secondary attribution: say "is said to have put it".

## Illustrations are real simulations
- Man: seeded 2D walk (seed 3370) that first returns home at step 286.
- Bird: seeded 3D walk (seed 23) with no return within 20,000 steps (the first 420 are drawn).
- Swarm: 12 seeded 3D walks (seeds 3088 to 3099), each drawn until its first return to the origin or 3,000 steps. 4 of 12 return (at steps 44, 166, 168 and 250). This block was chosen as representative (the expected fraction is about a third, and returned loops long enough to see) and is labelled as a simulation on screen.
