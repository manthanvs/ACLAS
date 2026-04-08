## Research Foundation: How These Papers Provide the Theoretical and Empirical Base for ACLAS

**ACLAS** (Adaptive Coding Lifecycle Analytics System) is not just a productivity tracker — it is deliberately grounded in decades of empirical research from computer science education, software engineering, and human factors in programming. The five research papers stored in the repository directly inspired and justified the core features of ACLAS:

- Real-time keystroke & activity tracking  
- Heartbeat-based telemetry (every 30 seconds)  
- Error / build-failure logging  
- Repeated-error analysis  
- Stress-score algorithm  
- Flow vs. frustration detection  

Below is the explicit mapping.

### 1. Jadud (2006) – Novice Compilation Behaviour
**Paper**: *An Exploration of Novice Compilation Behaviour in BlueJ* (Matthew C. Jadud, PhD Dissertation, 2006)  
(and the earlier conference version: *An Exploration of Novice Compilation Behaviour in BlueJ*)

**Key Insight**: Novice programmers repeatedly make the same syntax and semantic errors in short edit–compile–debug cycles. Jadud showed that studying these micro-behaviours reveals learning patterns and frustration points.

**How it bases ACLAS**:
- Directly inspired the **real-time heartbeat mechanism** (30-second intervals) and tracking of file switches, keystrokes, idle/active time, and compilation events.
- The VS Code extension essentially modernises Jadud’s BlueJ instrumentation for today’s most popular editor.

### 2. Becker et al. (2016) – Repeated Error Density Metric
**Paper**: *A New Metric to Quantify Repeated Compiler Errors for Novice Programmers* (Brett A. Becker et al., 2016)

**Key Insight**: Introduced the **Repeated Error Density (RED)** metric. Students who repeatedly commit the same compiler errors show significantly higher struggle and lower learning gains.

**How it bases ACLAS**:
- Forms the **mathematical foundation** of ACLAS’s **Stress Score**.
- Repeated errors, undos, and rapid error–fix loops are given higher weights in the stress calculation exactly because this paper proved they are strong indicators of cognitive overload and frustration.

### 3. Seo et al. (2014) – Programmers’ Build Errors at Google
**Paper**: *Programmers’ Build Errors: A Case Study (at Google)* (Hyunmin Seo et al., ICSE 2014)

**Key Insight**: Even at Google, ~30 % of Java builds (and higher for C++) fail. Certain error types consume disproportionate developer time.

**How it bases ACLAS**:
- Justifies tracking **build/compilation failures** and resolution time even for professional or advanced student developers.
- ACLAS brings large-scale industrial error analytics down to the individual developer level via the dashboard.

### 4. Müller & Fritz (2015) – Sensing Developers’ Emotions
**Paper**: *Stuck and Frustrated or In Flow and Happy: Sensing Developers’ Emotions and Progress* (Sebastian C. Müller & Thomas Fritz, ICSE 2015)

**Key Insight**: Developers’ emotional states (frustrated/stuck vs. in flow/happy) can be reliably inferred from interaction patterns and activity data. Frustration strongly correlates with reduced productivity and specific behavioural signals.

**How it bases ACLAS**:
- Provides the strongest justification for the **overall stress/frustration scoring system**.
- While the paper used biometrics, ACLAS uses rich behavioural proxies (keystroke dynamics, error frequency, idle time, repeated actions) — precisely the non-intrusive signals the authors recommend for practical deployment.

### Summary Table: Research → ACLAS Feature

| Research Paper                          | Core Contribution                          | ACLAS Feature(s) Directly Supported                  |
|-----------------------------------------|--------------------------------------------|-------------------------------------------------------|
| Jadud (2006)                            | Edit-compile cycles & novice behaviour     | Real-time heartbeat, keystroke logging, file switches, idle/active time |
| Becker et al. (2016)                    | Repeated Error Density (RED) metric        | Stress Score algorithm (repeated errors weighting)   |
| Seo et al. (2014, Google)               | Industrial build error statistics          | Build/compilation error tracking & analytics         |
| Müller & Fritz (2015)                   | Sensing frustration vs. flow               | Stress Score + affective analytics dashboard         |

---