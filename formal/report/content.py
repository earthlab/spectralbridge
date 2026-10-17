"""Human-facing narrative, exact proof references and figure interpretation."""

PAGES = []


def page(title, blocks=(), fig=None, caption=None, refs=(), table=None):
    PAGES.append(
        dict(
            title=title,
            blocks=list(blocks),
            figure=fig,
            caption=caption,
            refs=list(refs),
            table=table,
        )
    )


def B(label, text):
    return (label, text)


def C(look, notice, means, notmeans):
    return [
        ("What am I looking at?", look),
        ("What should I notice?", notice),
        ("What does it mean?", means),
        ("What does it NOT mean?", notmeans),
    ]


page(
    "What did we prove?",
    [
        B(
            "",
            "SpectralBridge moves spectral information among sensors and uses that information to distinguish and quantify ecological cover categories. The formal verification asks a simple question: when we transform a spectrum, which scientific properties are mathematically guaranteed to survive? The answer is both reassuring and limiting.",
        ),
        B(
            "",
            "Under appropriate assumptions, fixed linear and affine sensor transformations preserve the proportions of an ideal spectral mixture. But reducing spectral information can make different mixtures indistinguishable. Composition can survive the forward transformation even when it can no longer be uniquely recovered from the transformed observation.",
        ),
        B(
            "The whole story",
            "Observation → correction → sensor translation → spectral library → mixture inference → reconstruction or prediction → abundance interpretation. Some arrows follow exact algebra. Others depend on scene fitting, masks, calibration, reference selection and biological evidence. The entire operational chain has not been proved physically correct.",
        ),
        B(
            "Six questions that must stay separate",
            "Preservation: do the original weights still satisfy the transformed mixture equation? Information: which spectral distinctions remain observable? Identifiability: can only one allowed composition explain the observation? Reconstruction: how closely does a proposed mixture match the spectrum? Prediction: how accurate is a learned fraction estimate on new targets? Field validity: do those numbers correspond to independently measured cover?",
        ),
        B(
            "What was checked",
            "The existing layer contains 106 theorem declarations, accepted by Lean with only its standard mathematical foundations. Nine exact rational bridge cases are compared with Python calculations; four additional tests expose current audit boundaries. These are useful connections between equations and software, not a proof of all floating-point executions.",
        ),
        B(
            "How to read this report",
            "Blue anchors the proved algebra. Green marks conditional mathematical models, gray numerical checks, and warm brown empirical or data-dependent steps. Every toy spectrum is explicitly hypothetical; every empirical number comes from the canonical validation outputs. No new scientific models or theorems were fitted or added for this explanation.",
        ),
        B(
            "The central result",
            "SpectralBridge can preserve composition while losing identifiability. Mathematical coherence is valuable precisely because it makes the limits of interpretation harder to overlook.",
        ),
    ],
    refs=[
        "Core.linear_mixture",
        "Core.affine_mixture",
        "Inference.rank_cannot_increase",
        "Counterexamples.convolution_destroys_identifiability",
    ],
)
page(
    "The whole pipeline: local guarantees, shared assumptions",
    [
        B(
            "The idea",
            "NEON/AOP begins with packaged reflectance, not a formally verified radiance-to-reflectance inversion. Corrected NEON can be convolved to synthetic OLI or MicaSense products. Native drone observations follow a separate wavelength-mapped affine translation. Actual Landsat is an independent comparison path, not another synthetic observation.",
        ),
        B(
            "What this means for a scientist",
            "The diagram marks the kind of support available at each stage. A conditional algebraic result can be exact while its sensor or biological interpretation still needs evidence. Gray numerical checks are an additional kind of evidence, not a substitute for the warm empirical steps.",
        ),
    ],
    fig=1,
    caption=C(
        "The actual NEON, drone and independent Landsat paths.",
        "Fits, masks and medians sit between locally tractable operations.",
        "Apply a theorem only where its hypotheses match the stage and support.",
        "The whole pipeline is not certified as one linear or physically correct operator.",
    ),
    refs=["TRACEABILITY", "Pipeline.full_pipeline_conditional"],
)
page(
    "1 | Tests ask about examples; proofs ask about every valid case",
    [
        B(
            "The idea",
            "A conventional unit test asks, “Did this example produce the expected answer?” A proof asks, “For every input satisfying these assumptions, must this property hold?” SpectralBridge uses both. Lean is a checker of explicitly written mathematical arguments; it does not inspect a landscape or decide whether a category label is true.",
        ),
        B(
            "What was actually checked",
            "The full root import builds all 106 declarations. An axiom audit lists the foundational dependencies of each result: choice, propositional extensionality and quotient soundness. These are mathematical foundations, not added assumptions that sensors are calibrated or plants are pure. No custom axiom or unfinished proof is used.",
        ),
        B(
            "The implementation bridge",
            "Lean evaluates nine rational cases: response weighting, multiplication, affine translation, footprint mean, synthetic mixture, FCLS oracle, MESMA search, ridge prediction and simplex projection. Python calls the corresponding functions, including toy file-writing paths. Float32 checks allow 10⁻⁶ or 10⁻⁵ absolute error; most float64 checks use 10⁻¹⁰ to 10⁻¹² or tighter.",
        ),
    ],
    fig=14,
    caption=C(
        "Dots are checked examples inside the hypotheses of a mathematical claim.",
        "A proof covers a stated domain; tests sample computations.",
        "Agreement supports implementation conformance for those cases.",
        "The sorting algorithm, active-face solver and arbitrary IEEE execution are not universally certified.",
    ),
    refs=["AXIOMS", "BRIDGE", "CONFORMANCE"],
)
page(
    "2 | Spectra, vectors and the geometry of fractions",
    [
        B(
            "The idea",
            "A plotted curve and its ordered list of band values are two views of the same sampled spectrum. The mathematical vector records the values and their positions; wavelength metadata supplies their physical meaning. Real-valued vectors cannot themselves certify units, calibration or field provenance.",
        ),
        B("The mathematics", "x = [x₁, x₂, …, xₙ]     and     y = 0.6 A + 0.4 B"),
        B(
            "In plain language:",
            "Take 60% of every coordinate of A and 40% of the same coordinate of B. The mixture curve is computed coordinate by coordinate, without inventing a new biological observation.",
        ),
        B(
            "Valid fractions",
            "A fraction vector is in the simplex when every entry is nonnegative and all entries add to one. Three fractions occupy a triangle: corners are pure components, edges contain two-component mixtures, and the interior contains three-component mixtures. “Pure” here means an algebraic corner, not evidence of biological purity.",
        ),
    ],
    fig=2,
    caption=C(
        "Hypothetical spectral curves and a three-component fraction triangle.",
        "The 60/40 point lies on the A/B edge.",
        "Simplex constraints express valid proportions and put ideal mixtures in the endmember convex hull.",
        "The curves are not measured vegetation spectra, and simplex membership does not establish field cover.",
    ),
    refs=["Core.pair_simplex", "Core.triple_simplex", "Inference.mixture_convexHull"],
)
page(
    "3 | Mix first or change sensors first: the same endpoint",
    [
        B(
            "The idea",
            "A fixed linear transformation combines spectral coordinates with fixed coefficients. Sampled sensor response weighting is such an operation on a common valid support. Scaling a spectrum or selecting fixed bands is also linear.",
        ),
        B("The mathematics", "T(Σ fᵢ xᵢ) = Σ fᵢ T(xᵢ)"),
        B(
            "In plain language:",
            "Transforming a mixture gives the same result as transforming each ingredient first and then mixing with the original weights. This is the preservation guarantee: the original fractions still solve the forward equation.",
        ),
        B(
            "Connection to SpectralBridge",
            "The exact toy operator in the figure adds two coordinates. It makes the commutation visible without pretending to be a Landsat response. The general proof also applies to fixed OLI/MicaSense convolution matrices and fixed multiplicative adjustments, provided target and references receive the same transformation and use the same support.",
        ),
    ],
    fig=3,
    caption=C(
        "Two routes through the proved two-coordinate toy calculation.",
        "Both routes finish at 1 using the same 60/40 weights.",
        "Fixed linear operations preserve the mixture equation.",
        "The endpoint does not necessarily reveal which weights produced it.",
    ),
    refs=[
        "Core.linear_zero",
        "Core.linear_add",
        "Core.linear_smul",
        "Core.linear_mixture",
        "Counterexamples.sumSensor",
    ],
)
page(
    "Sensor response: a weighted sum, with a real implementation guard",
    [
        B(
            "The idea",
            "The inline pipeline samples Gaussian responses at the supplied wavelengths, using packaged band centers and full widths at half maximum. “Straight” resampling uses the nearest coordinate. It does not integrate a continuous measured response curve; the discrete formula is the contract being explained.",
        ),
        B("The mathematics", "wᵢ = rᵢ / (Σ r + ε),   ε = 10⁻¹²;     output = Σ wᵢ xᵢ"),
        B(
            "In plain language:",
            "A band is a weighted combination of input coordinates. Nonnegative weights summing exactly to one preserve constants and keep outputs between input bounds. The actual epsilon denominator makes the weights sum to response_sum / (response_sum + epsilon), so exact constant preservation does not follow.",
        ),
        B(
            "What the proof establishes",
            "The fixed-weight operation remains linear. For a constant input, the exact-real attenuation factor is proved. When sampled support is tiny, attenuation can be large; the Python near-zero-response example reproduces it. This is not evidence that ordinary production bands have tiny support.",
        ),
    ],
    fig=15,
    caption=C(
        "The proved constant-input factor as sampled response support changes.",
        "At response sum 10⁻¹⁴, the output is about 0.0099 of the constant input.",
        "Normalization details matter independently of linearity.",
        "This curve is not an observed calibration error or a measured sensor response.",
    ),
    refs=[
        "Core.weighted_bounds",
        "Core.normalized_constant",
        "Core.epsilon_constant",
        "PY_RESPONSE",
    ],
)
page(
    "4 | Why an intercept can preserve convex mixtures",
    [
        B(
            "The idea",
            "An affine map first applies a linear transformation and then adds an offset. Offsets might seem to break mixture algebra, but a shared offset is added exactly once when the mixture weights total one.",
        ),
        B(
            "The mathematics",
            "T(x) = A x + b;   Σ fᵢ(A xᵢ + b) = A Σ fᵢxᵢ + b Σ fᵢ = A Σ fᵢxᵢ + b",
        ),
        B(
            "In plain language:",
            "Because fractions sum to one, the component offsets add to one common offset. The same affine translation can shift all spectra while retaining their ideal mixture proportions.",
        ),
        B(
            "The exact condition",
            "Sum-to-one is sufficient. More generally, commutation holds exactly when b = (sum of weights) × b. A zero offset therefore works without normalized weights. Applying different fitted offsets to different ingredients is not covered.",
        ),
        B(
            "Connection to SpectralBridge",
            "Native MicaSense-to-Landsat-like translation applies mapped per-band slopes and intercepts. This is distinct from packaged percentage adjustments applied to synthetic Landsat products relative to MicaSense. Neither equation proves that the empirical coefficients transfer to independent sensors.",
        ),
    ],
    refs=[
        "Core.affine_mixture_defect",
        "Core.affine_mixture",
        "Core.affine_mixture_iff",
        "TRANSLATIONS",
    ],
    table="translations1",
)
page(
    "The transformations that do - and do not - fit the theorem",
    [
        B(
            "The implementation matters",
            "Frozen SCS+C and BRDF factors are diagonal multipliers at a location. Their algebra is simple, but the factors come from geometry and fitted parameters; optional NDVI bins can change with the data. Scene percentile matching and regression brightness estimation are also data-dependent. Default clipping makes even a frozen affine brightness step nonlinear when clipping is active.",
        ),
        B(
            "The ordering is real",
            "The correction core applies topography, then BRDF, then an optional additive offset. Two fixed diagonal multipliers commute. An offset and a multiplier generally do not: scaling 3 + 1 by 2 gives 8, while scaling 3 first and then adding 1 gives 7.",
        ),
        B(
            "Aggregation is not interchangeable",
            "Actual Landsat common-footprint means use normalized area weights on fixed joint-valid support. The primary polygon/year library instead uses hierarchical medians. A proved counterexample has medians of [0,0,1] and [0,1,0] both zero, but the median of their sum [0,1,1] is one. Do not use the mean theorem to reorder median aggregation and cross-band mixing.",
        ),
    ],
    refs=[
        "Core.mean_affine",
        "Core.multipliers_commute",
        "Core.order_matters",
        "Core.median_not_additive",
        "Core.clipping_not_mixture",
        "TRANSLATIONS",
    ],
    table="translations2",
)
page(
    "5 | The central surprise: a distinction can disappear",
    [
        B(
            "The idea",
            "A forward transformation can be mathematically correct and still discard the dimensions that distinguish materials. The exact proved example starts with A = [1,0] and B = [0,1]. Their two-coordinate mixtures identify the A/B fraction. The sensor then adds those two coordinates.",
        ),
        B(
            "The mathematics",
            "T([x₁,x₂]) = x₁ + x₂;    T(A) = T(B) = 1;    rank(T E) ≤ rank(E)",
        ),
        B(
            "In plain language:",
            "Every A/B mixture produces the same summed measurement. The weights still satisfy the transformed mixture equation, but that equation now has many answers. A fixed linear transformation cannot create rank that the original library lacked.",
        ),
        B(
            "What this means for a scientist",
            "A many-to-fewer-band linear map is noninjective on the whole input space. It may still distinguish a particular restricted library; fewer bands do not prove that every real mixture is ambiguous. The counterexample proves possibility, not the failure rate of OLI.",
        ),
    ],
    fig=4,
    caption=C(
        "The exact two-to-one-coordinate counterexample in the Lean files.",
        "Distinct inputs collapse to one identical sensor value.",
        "COMPOSITION CAN BE PRESERVED WHILE IDENTIFIABILITY IS LOST.",
        "The toy sum is not an actual OLI band, and it does not prove all OLI mixtures are nonidentifiable.",
    ),
    refs=[
        "Inference.rank_cannot_increase",
        "Inference.fewer_bands_not_injective",
        "Counterexamples.hyperspectral_identifiable",
        "Counterexamples.convolution_destroys_identifiability",
    ],
)
page(
    "6 | One spectrum can have more than one composition",
    [
        B(
            "The idea",
            "Identifiability asks whether different allowed fraction vectors can give exactly the same spectrum. It is a property of the reference system and observation model, not simply a low residual from one fitted solution.",
        ),
        B(
            "The mathematics",
            "A = [1,0], B = [0,1], C = [0.5,0.5];     0.5 A + 0.5 B = C",
        ),
        B(
            "In plain language:",
            "A half-and-half A/B mixture and a pure C reference produce the same two-coordinate observation. Both have valid fractions; both reconstruct exactly. The observation cannot select a unique answer.",
        ),
        B(
            "Connection to SpectralBridge",
            "The proved example uses a singleton class system and a two-class system, matching the logic of alternative candidate compositions in the MESMA diagnostic. It does not assert that any specific biological material is literally the midpoint of two others. In real data, near equality, noise and reference variability can make the practical distinction harder still.",
        ),
    ],
    fig=5,
    caption=C(
        "The exact three-reference ambiguity example.",
        "Two different category fraction vectors reach the same observation.",
        "Zero reconstruction error does not guarantee a unique composition.",
        "Toy labels A/B/C are not independently validated biological categories.",
    ),
    refs=[
        "Counterexamples.ambiguous_reconstruction",
        "Counterexamples.reconstruction_not_identifiability",
        "Counterexamples.mesma_ambiguity",
    ],
)
page(
    "7 | FCLS: find the closest allowed spectral mixture",
    [
        B(
            "The idea",
            "Fully Constrained Least Squares takes a fixed set of endmembers and finds nonnegative fractions adding to one that best reconstruct the observed spectrum. The endmembers define a convex feasible region in spectral space.",
        ),
        B("The mathematics", "minimize ||y − E f||²,   with fᵢ ≥ 0 and Σ fᵢ = 1"),
        B(
            "In plain language:",
            "Choose the allowed mixture whose predicted spectrum is closest to the observation. Dividing squared error by the number of bands changes the scale of the objective but not its minimizer when band count is positive.",
        ),
        B(
            "What is proved",
            "The ideal feasible set is convex and compact, the objective is convex, and a minimizer exists when there is at least one component. Uniqueness follows under identifiability. If the supplied references are the true generating references and the mixture model is exact and identifiable, the ideal solver recovers the generating fractions.",
        ),
    ],
    fig=6,
    caption=C(
        "A hypothetical two-coordinate spectral triangle and a target outside it.",
        "The closest feasible point is a reconstruction, not a measured fraction truth.",
        "The solver works when given the right ingredients and an identifiable ideal model.",
        "The oracle theorem does not validate reference purity, physical mixing or field abundance.",
    ),
    refs=[
        "Inference.fcls_exists",
        "Inference.fcls_convex",
        "Inference.fcls_unique",
        "Inference.fcls_exact_recovery",
        "ORACLE",
    ],
)
page(
    "8 | MESMA: search among plausible reference combinations",
    [
        B(
            "The idea",
            "MESMA adds a candidate-library search around constrained fitting. In the actual utility, default models contain up to three different categories, one retained reference per category, with a 20,000-model guard. Boundary faces are considered explicitly; near-singular and tiny-interior candidates can be excluded by numerical thresholds.",
        ),
        B(
            "The mathematics",
            "Near-fit set = saved candidate fractions with RMSE ≤ chosen RMSE + 0.01",
        ),
        B(
            "In plain language:",
            "Several admitted class compositions may fit almost as well as the selected one. The formal tolerance-aware search theorem bounds the chosen cost relative to admitted costs; it is not a guarantee about every physical composition.",
        ),
        B(
            "What is actually saved",
            "The implementation keeps one best fraction solution per class set, then summarizes ranges among near-fitting class sets. Those ranges are a restricted candidate diagnostic. Increasing the tolerance can enlarge the mathematical near-fit set; it cannot make uniqueness more secure.",
        ),
    ],
    fig=7,
    caption=C(
        "The exact C versus A/B ambiguity, surrounded by a conceptual candidate search.",
        "A winner and an equally good alternative can coexist.",
        "MESMA optimizes spectral reconstruction within the retained search.",
        "Saved ranges are not exhaustive physical uncertainty or proof of biological truth.",
    ),
    refs=[
        "Inference.tolerant_search_bound",
        "Inference.ambiguity_mono",
        "Inference.selected_feasible",
        "PY_MIXTURE",
    ],
)
page(
    "9 | Ridge learns a fraction predictor",
    [
        B(
            "The idea",
            "Ridge uses training spectra and known synthetic fraction targets to learn a regularized mapping. It is a supervised prediction problem, whereas MESMA searches reference mixtures to reconstruct each target spectrum. A ridge prediction is a learned estimate under the training distribution, not a proof of a unique conditional expectation.",
        ),
        B("The mathematics", "minimize ||F_c − X_c B||² + α ||B||²,   α > 0"),
        B(
            "In plain language:",
            "Fit fractions while penalizing very large coefficients. The centered training design and targets, positive penalty and fixed preprocessing give a unique coefficient minimizer for each output column. The benchmark fits an unpenalized intercept and restores it during prediction.",
        ),
        B(
            "Connection to SpectralBridge",
            "Standardization is fitted on proper-training mixtures only. Alpha is chosen from 0.1 and 10 on calibration mixtures, not target truth. A fixed trained model returns one prediction even if multiple compositions could produce that spectrum. UNIQUE MODEL FIT does not mean UNIQUE PHYSICAL COMPOSITION.",
        ),
    ],
    fig=8,
    caption=C(
        "The actual distinction between candidate reconstruction and supervised prediction.",
        "The two methods optimize different targets.",
        "A unique ridge fit can improve expected synthetic prediction error without resolving inverse ambiguity.",
        "No theorem says ridge is universally superior to MESMA.",
    ),
    refs=[
        "Ridge.ridge_positive",
        "Ridge.ridge_normal_equation",
        "Ridge.ridge_minimizer_unique",
        "Counterexamples.perfect_prediction_not_unique_inversion",
        "PY_RIDGE",
    ],
)
page(
    "10 | Projection imposes valid fraction geometry",
    [
        B(
            "The idea",
            "Unconstrained ridge predictions can be negative or fail to sum to one. Euclidean simplex projection chooses the nearest fraction vector that is nonnegative and sums to one. It is more than clipping negatives: the entries must be adjusted together.",
        ),
        B(
            "The mathematics",
            "p = nearest feasible fraction vector to x;     ||p − f*|| ≤ ||x − f*|| for feasible truth f*",
        ),
        B(
            "In plain language:",
            "The ideal projection cannot increase Euclidean distance to any truth already in the simplex. It returns valid fractions, leaves valid inputs unchanged and is idempotent: projecting again changes nothing.",
        ),
        B(
            "What is and is not verified",
            "The Lean result uses the Euclidean metric, not the default norm on a function vector. A threshold-form certificate and an exact toy certificate connect to the sorting rule. General sorting/rank-index and arbitrary floating-point equivalence are not fully proved; representative Python checks support that bridge.",
        ),
    ],
    fig=9,
    caption=C(
        "A hypothetical sum-one fraction plane; the raw point has a negative A entry.",
        "Projection moves to the nearest valid point; dotted lines show distance to a feasible truth.",
        "Valid constraints can improve fraction error without adding spectral measurements.",
        "Projection does not recover information lost by convolution or eliminate candidate ambiguity.",
    ),
    refs=[
        "Projection.projection_unique",
        "Projection.projection_mem",
        "Projection.projection_idempotent",
        "Projection.simplex_projection_error",
        "Bridge.projection_certificate",
    ],
)
page(
    "11 | The full chain is a conditional scientific argument",
    [
        B(
            "The idea",
            "The composition theorem requires preserved generating mixtures, appropriate references, transformed identifiability and an ideal constrained optimizer. These are explicit hypotheses, not facts proved for every scene.",
        ),
        B(
            "The mathematics",
            "Correct generating model + preserved mixture + transformed identifiability + ideal solver ⇒ generating fractions recovered",
        ),
        B(
            "In plain language:",
            "Recovery follows when the hypotheses hold. Scene-dependent correction, masks or medians can break preservation. Ridge prediction is not substituted for the ideal FCLS solver.",
        ),
    ],
    fig=10,
    caption=C(
        "An ideal 60/40 story with preservation, loss, assumptions and estimation marked separately.",
        "Fewer measurements and added empirical assumptions enter at different places.",
        "Use the composition theorem as an assumption checklist, not an operational approval stamp.",
        "Neither the physical landscape nor the complete Python workflow has been certified by this diagram.",
    ),
    refs=[
        "Inference.pipeline_recovery",
        "Pipeline.full_pipeline_conditional",
        "ASSUMPTIONS",
    ],
)
page(
    "12 | What the proof says about the observed results",
    [
        B(
            "Separability is empirical",
            "The canonical analysis finds differences for all ten researcher-category pairs in acquisition-matched sampled comparisons. The five labels are Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, and Woody shrub. Lean does not establish that biological or statistical finding; background/dead cover is a comparator rather than a biological PFT.",
        ),
        B(
            "Recognition is not mixture identifiability",
            "The classifiers identify unseen labelled polygons with useful but imperfect balanced accuracy. Geographic transfer is weaker. Synthetic OLI retains signal, but recognition drops relative to full NEON. The formal rank-loss result explains a possible mechanism, not a causal attribution of the entire observed accuracy gap.",
        ),
        B(
            "Reading the evidence",
            "Points below are means of the saved outer scores, not confidence intervals. New polygons and held sites are distinct validation questions. Synthetic OLI is derived from the same corrected NEON source; it is not an independent Landsat acquisition.",
        ),
    ],
    fig=12,
    caption=C(
        "Canonical full-NEON/synthetic-OLI recognition and NEON synthetic-fraction error.",
        "The held-site recognition penalty and the global-year ridge/prior failure remain visible.",
        "The empirical outcomes are compatible with information loss and library-dependent prediction.",
        "A mathematical possibility is not proof of the cause, universality or field validity of these outcomes.",
    ),
    refs=["EMP_RECOGNITION", "EMP_ABUNDANCE", "SCIENTIFIC_REPORT"],
)
page(
    "The abundance controls make the interpretation sharper",
    [
        B(
            "The oracle",
            "Known-generating-parent FCLS produces nearly zero synthetic fraction error. This is expected when exact linear mixtures, common representation, appropriate references and identifiability hold. It tests an ideal numerical case, not independently measured field cover.",
        ),
        B(
            "Ridge120 and the matched15 control",
            "The larger-parent ridge benchmark reduces mean-fold synthetic error relative to MESMA15. Restricting ridge to the exact 15 MESMA parents removes the mean NEON advantage. Retained diversity, training bundles and model priors also change, so the control does not isolate one causal mechanism or prove intrinsic algorithm superiority.",
        ),
        B(
            "The global-year prior",
            "Global-year ridge fails the no-spectrum prior on average. A predictor can therefore be mathematically well defined and still be less useful than a simple baseline under domain change. Retrospective labels and site/year composition also limit annual biological interpretations.",
        ),
        B(
            "How proof and evidence fit",
            "The formal ambiguity example explains why low residual alone cannot validate composition. The projection theorem explains why valid-fraction geometry can help error. Neither theorem selects a universal estimator winner. All abundance values here are controlled synthetic algebraic fractions; independent field fractional-cover validation remains outstanding.",
        ),
        B(
            "A concrete objective mismatch",
            "Suppose the true category is A at observed [0,0], but the retained A reference is [1,1] and B is [0,0]. Choosing B reconstructs perfectly while assigning the wrong category. Choosing A has larger spectral residual but correct class fractions. The formal counterexample separates these two losses; it does not assume the retained library is the true generating library.",
        ),
    ],
    refs=[
        "EMP_ABUNDANCE",
        "EMP_MATCHED",
        "ORACLE",
        "Counterexamples.residual_does_not_order_abundance_error",
        "SCIENTIFIC_REPORT",
    ],
    table="abundance",
)
page(
    "13 | The implementation audit found consequential discrepancies",
    [
        B(
            "The idea",
            "A coherent mathematical specification does not prove that every array operation implements it correctly. The audit found reproducible departures from expected axis and pixel-identity contracts. They must be investigated, not dismissed because other tests or proofs pass.",
        ),
        B(
            "What was reproduced",
            "For a band-first cube with shape (7,2,3), the brightness helper selects the smallest dimension - the two image rows - as its band axis. For a 3×3 raster with chunk size four, overlapping extraction windows emit 15 rows for nine unique pixels.",
        ),
        B(
            "What we can conclude",
            "Both fixtures can change outputs in affected executions. Their impact on existing scientific results is not yet established. No historical output was replaced, and production fixes remain queued separately. The following pages account for every documented discrepancy and boundary, including issues that are not bugs.",
        ),
    ],
    fig=13,
    caption=C(
        "The actual two audit fixtures, with pixel emission counts in the right panel.",
        "A spatial axis is mistaken for bands; some raster rows are emitted twice.",
        "These are concrete implementation concerns requiring explicit contracts and provenance review.",
        "The fixtures do not show that the supplied historical library used either affected path.",
    ),
    refs=["AUDIT", "CONFORMANCE"],
)
AUDITS = [
    (
        "A1 | Band-axis inference",
        "The percentage-brightness helper chooses the smallest array dimension as bands. A (7,2,3) band-first cube is moved so its two image rows become the apparent bands.",
        "Each known band should receive its own coefficient, independent of image size.",
        "Array shape is used as a proxy for the semantic band axis.",
        "Yes. Gains can be applied across rows and only two coefficients used. The small fixture reproduces this.",
        "Impact not yet established. Trace actual product shapes and the generating code path.",
        "High; confirmed toy reproduction.",
        "Use an explicit band-axis contract, test both layouts and edge shapes, then audit affected product provenance.",
    ),
    (
        "A2 | Overlapping extraction windows",
        "Chunk starts and ends use integer row conversion with an extra end row. Consecutive windows overlap; the 3×3 fixture emits 15 rows for nine pixels.",
        "Each selected raster/pixel identity should occur once.",
        "Flat chunk boundaries are converted to whole-row windows without trimming duplicated rows.",
        "Yes. Counts and downstream summaries can change; weighting duplicated pixels may alter medians.",
        "Impact not yet established. Determine whether the historical library used this extractor and whether duplicates were removed.",
        "High; confirmed toy reproduction.",
        "Use disjoint row blocks or trimmed flat windows, assert unique source/pixel keys, quantify impacts before creating new versioned outputs.",
    ),
    (
        "A3 | Response normalization",
        "Inline convolution divides by response sum plus 10⁻¹². Zero support produces zero; negative weights are not rejected.",
        "An exact normalized nonnegative average preserves constants and bounds.",
        "The stabilizing denominator changes the normalization; the exact-real factor is sum/(sum+epsilon).",
        "Yes, strongly when support is tiny. Ordinary well-supported bands may have negligible differences.",
        "Impact not yet established; the near-zero toy is not a measured production-band error.",
        "Low for ordinary support; high for near-zero support.",
        "Validate response sign/support and choose an explicit zero-support policy; retain the epsilon-specific theorem until implementation changes.",
    ),
    (
        "A4 | Fitted corrections are data-dependent",
        "SCS+C fits coefficients; BRDF can choose NDVI bins; scene brightness fits parameters and usually clips.",
        "A linear theorem requires one fixed operator on common support.",
        "Re-estimation, bin selection and clipping can change the operator with its input.",
        "Yes if an analyst reorders operations or assumes full-pipeline linearity. This is not itself an implementation bug.",
        "Impact not yet established for any improper reorder; the existing ordering is preserved.",
        "Specification boundary.",
        "State frozen-parameter hypotheses and retain the documented correction order.",
    ),
    (
        "A5 | MESMA is a restricted numerical search",
        "The code limits categories/models, excludes tiny interiors, skips numerically weak Gram systems and updates only beyond a 10⁻¹⁴ MSE improvement.",
        "An unrestricted exact argmin ranges over every mathematically allowed candidate.",
        "The executed search admits only a finite, thresholded subset and uses a tie tolerance.",
        "Yes relative to an unrestricted ideal solver, particularly near boundaries or degeneracy.",
        "Impact not yet established beyond documented solver controls; exact-real optimality is not asserted for Python.",
        "Specification boundary, not automatically a bug.",
        "Use the admitted-search tolerance theorem; retain rank/interior/tie settings and avoid unrestricted-optimum claims.",
    ),
    (
        "A6 | Ambiguity is not exhaustive uncertainty",
        "One best fraction solution is stored per class set; near-fit ranges use those solutions within chosen RMSE + 0.01.",
        "All feasible near-optimal fractions would define a larger uncertainty question.",
        "The saved diagnostic samples candidate-class-set winners, not every feasible composition.",
        "It changes which alternatives are represented; it need not change the selected estimate.",
        "The existing diagnostic is not an exhaustive physical interval. Broader field impact is not established.",
        "Interpretation limitation.",
        "Name the retained library, metric, tolerance and restricted range; do not call it full physical uncertainty.",
    ),
    (
        "A7 | Centering and intercept matter",
        "Ridge uses proper-training standardization, fit_intercept=True and calibration-selected alpha.",
        "The inverse formula must use centered transformed design/targets and restore the unpenalized intercept.",
        "A naive uncentered formula describes a different model.",
        "Yes if the wrong formula is used for replay or explanation; the audited implementation uses the stated conventions.",
        "No leakage was found in inspected preprocessing code; this is inspection/numerical evidence, not a workflow proof.",
        "Specification boundary.",
        "Keep means, scales, centering, alpha and intercept in replay provenance; use the proved centered objective.",
    ),
    (
        "A8 | Library medians are not means",
        "Extraction emits pixels; the primary library aggregates hierarchical medians with unsupported bands missing.",
        "The mean commutation theorem applies to normalized arithmetic averaging on fixed support.",
        "Medians are nonlinear under arbitrary addition/cross-band mixing.",
        "Yes if a mean theorem is used to reorder median aggregation and transformation.",
        "Impact not yet established for any altered order; no aggregation was changed.",
        "Interpretation limitation.",
        "Describe actual medians and common support; use the proved median counterexample rather than a mean claim.",
    ),
    (
        "A9 | Multiple response backends",
        "Inline Gaussian sampling, input-width-weighted legacy fallback and optional HyTools implementations differ; the legacy wrapper assumes 426 bands/FWHM5.",
        "A coefficient-equivalence claim would require the same actual coefficient construction.",
        "Backends and defaults encode different approximations and metadata assumptions.",
        "Yes. Frozen matrices can all be linear while producing different numbers.",
        "Impact not yet established across historical backends.",
        "Implementation boundary.",
        "Record backend/version/input metadata, pin optional dependencies and do not claim universal coefficient equivalence.",
    ),
    (
        "A10 | Synthetic coefficients are not independent calibration",
        "The packaged drone registry was fitted between synthetic products from corrected NEON; range checks guard numerical compatibility.",
        "Physical calibration transfer requires independent aligned native-sensor observations.",
        "A complete synthetic fit or high correlation does not establish empirical cross-sensor validity.",
        "Applied coefficients change outputs; physical correctness is not established by their algebra.",
        "Native-drone/actual-Landsat validity remains an empirical question.",
        "Metadata/scale interpretation limitation.",
        "Collect independent calibration/validation observations; retain diagnostic provenance and explicit sensor direction.",
    ),
    (
        "A11 | Missing data change the domain",
        "Inline products reset all-band nodata pixels; partial nodata/NaNs can enter sums. Extraction rejects -9999 but not every nonfinite value.",
        "Real-vector theorems require finite common support and aligned masks.",
        "Array missingness is not represented by a finite real number; masks can alter effective operators.",
        "Yes. Invalid values can propagate or contaminate weighted values.",
        "Impact not yet established; quantify actual partial-missing cases before judging a dataset.",
        "Masking/implementation boundary.",
        "Declare and test per-band support and nodata policies; preserve legitimate finite negative corrected values.",
    ),
    (
        "A12 | Optional brightness layout heuristic",
        "The scene-brightness helper treats the array as band-first when its first dimension is no larger than its last.",
        "Accepted layouts need a known band axis.",
        "A relative-size comparison cannot identify semantics for every shape.",
        "Yes for ambiguous shapes; fitting and clipping can compound interpretation differences.",
        "Impact not yet established; this finding is confirmed by inspection, not the separate A1 fixture.",
        "Potential axis defect; inspected boundary.",
        "Add an explicit axis contract and layout tests; do not treat default clipping as globally affine.",
    ),
    (
        "Startup | Lazy Parquet import",
        "The helper accesses pyarrow.parquet without explicitly importing that submodule. A fresh isolated run raised AttributeError.",
        "The advertised extraction path should initialize its own dependency.",
        "Execution can depend on whether another import has already loaded the submodule.",
        "It can prevent execution; it does not silently change a successfully produced spectrum.",
        "Impact not yet established. The overlap fixture imports the submodule explicitly to reach the loop.",
        "Execution/import-order issue.",
        "Import pyarrow.parquet inside the lazy helper and test a fresh process.",
    ),
    (
        "Precision | Rounded wavelength labels",
        "Decimal centers/FWHM enter inline construction as float32; polygon wavelength labels are rounded to integer nm.",
        "Response construction should use authoritative response metadata.",
        "A rounded column name omits decimal-center precision and the response width/function.",
        "Reconstructing an operator from labels alone can change results; ordinary labeling does not change prior convolution values.",
        "Impact not yet established for any metadata reconstruction. No coefficient-direction error was found in the inspected application.",
        "Metadata precision boundary.",
        "Use original header/configuration responses, preserve their hashes and distinguish labels from sensor definitions.",
    ),
]
for title, ids in [
    ("Audit details: the two reproduced contract failures", [0, 1]),
    ("Audit details: normalization, correction and search", [2, 3, 4]),
    ("Audit details: uncertainty, ridge and aggregation", [5, 6, 7]),
    ("Audit details: response, calibration and masks", [8, 9, 10]),
    ("Audit details: layout, imports and wavelength precision", [11, 12, 13]),
]:
    blocks = []
    for i in ids:
        name, code, expected, why, outputs, existing, severity, action = AUDITS[i]
        blocks.append(
            B(
                name,
                f"<b>What the code does:</b> {code}<br/><b>What the specification expects:</b> {expected}<br/><b>Why they differ:</b> {why}<br/><b>Can it change outputs?</b> {outputs}<br/><b>Can it change existing scientific results?</b> {existing}<br/><b>Severity:</b> {severity}<br/><b>Recommended action:</b> {action}",
            )
        )
    page(title, blocks, refs=["AUDIT", "CONFORMANCE", "TRACEABILITY"])
STATUS = [
    (
        "Fixed sensor weighting is linear",
        "PROVED IF ASSUMPTIONS HOLD",
        "Same finite weights and support; no physical response validation.",
        "Core.linear_mixture",
    ),
    (
        "Ideal linear maps preserve weights",
        "PROVED",
        "The forward weighted-sum equation commutes with any fixed linear map.",
        "Core.linear_mixture",
    ),
    (
        "Shared affine maps preserve simplex mixtures",
        "PROVED IF ASSUMPTIONS HOLD",
        "Sum-to-one or the exact offset-defect condition; same map on every component.",
        "Core.affine_mixture",
    ),
    (
        "Band reduction can destroy identifiability",
        "PROVED",
        "The exact two-coordinate counterexample loses the A/B distinction.",
        "Counterexamples.convolution_destroys_identifiability",
    ),
    (
        "Every fewer-band library loses uniqueness",
        "NOT ESTABLISHED",
        "Whole-space noninjectivity does not imply failure on every restricted mixture simplex.",
        "Inference.fewer_bands_not_injective",
    ),
    (
        "A mixture spectrum lies in the reference convex hull",
        "PROVED IF ASSUMPTIONS HOLD",
        "Nonnegative fractions total one; reference spectra use compatible coordinates.",
        "Inference.mixture_convexHull",
    ),
    (
        "FCLS minimizer exists and is unique",
        "PROVED IF ASSUMPTIONS HOLD",
        "Existence needs a nonempty finite simplex; uniqueness additionally needs identifiability.",
        "Inference.fcls_unique",
    ),
    (
        "Known-parent ideal recovery works",
        "PROVED IF ASSUMPTIONS HOLD",
        "True generating references, exact linear model, transformed identifiability, ideal solver.",
        "Inference.fcls_exact_recovery",
    ),
    (
        "Good reconstruction guarantees true composition",
        "FALSE / COUNTEREXAMPLE",
        "Pure C and half A/B reconstruct the same spectrum with different class fractions.",
        "Counterexamples.mesma_ambiguity",
    ),
    (
        "MESMA winner beats every physical mixture",
        "NOT ESTABLISHED",
        "The proved bound concerns admitted finite costs and a tolerance, not all biology.",
        "Inference.tolerant_search_bound",
    ),
    (
        "Positive-alpha ridge has unique fitted coefficients",
        "PROVED IF ASSUMPTIONS HOLD",
        "Fixed centered design/targets and positive regularization; restore the intercept.",
        "Ridge.ridge_minimizer_unique",
    ),
    (
        "One ridge prediction implies physical uniqueness",
        "FALSE / COUNTEREXAMPLE",
        "Perfect prediction can coexist with an ambiguous reference inverse.",
        "Counterexamples.perfect_prediction_not_unique_inversion",
    ),
    (
        "Ideal projection gives valid fractions",
        "PROVED",
        "Nonnegative entries total one; feasible predictions are fixed and projection is idempotent.",
        "Projection.projection_mem",
    ),
    (
        "Projection cannot worsen distance to feasible truth",
        "PROVED IF ASSUMPTIONS HOLD",
        "Euclidean projection and truth in the same nonempty simplex.",
        "Projection.simplex_projection_error",
    ),
    (
        "Python exactly matches the spec for every input",
        "NOT ESTABLISHED",
        "Nine rational examples agree numerically; full IEEE/sorting/active-face equivalence is not proved.",
        "CONFORMANCE",
    ),
    (
        "Representative Python calculations agree",
        "NUMERICALLY CHECKED",
        "Nine bridge cases plus four audit tests; declared per-case tolerances.",
        "CONFORMANCE",
    ),
    (
        "Sampled category spectra differ",
        "EMPIRICALLY SUPPORTED",
        "All ten pairs in the reported acquisition-matched design; not a Lean biological theorem.",
        "SCIENTIFIC_REPORT",
    ),
    (
        "Ridge is universally better than MESMA",
        "NOT ESTABLISHED",
        "Matched15 removes the mean NEON advantage; domain and library capacity matter.",
        "EMP_MATCHED",
    ),
    (
        "Calibration and field observations are correct",
        "NOT ESTABLISHED",
        "Algebra does not supply independent sensor or label truth.",
        "ASSUMPTIONS",
    ),
    (
        "Synthetic fractions establish field fractional cover",
        "NOT ESTABLISHED",
        "Independent contemporaneous field-fraction validation remains outstanding.",
        "SCIENTIFIC_REPORT",
    ),
]
page(
    "14 | What is actually proved? Mathematical statements",
    [
        B(
            "Read the status and its conditions together",
            "PROVED means an existing kernel-checked mathematical result. A conditional statement is still a proof, but its scientific use requires the listed hypotheses. Every proof-linked row below names an actual audited theorem in the machine-readable companion table. Nothing is labeled proved solely because it appeared in a plan.",
        )
    ],
    table="status1",
    refs=["PROOF_STATUS", "AXIOMS"],
)
page(
    "What is actually proved? Prediction and field interpretation",
    [
        B(
            "A guarantee has a domain",
            "NUMERICALLY CHECKED and EMPIRICALLY SUPPORTED mean different things from PROVED. A counterexample refutes a universal implication; it does not estimate how frequently a real deployment will fail. A missing empirical measurement cannot be repaired by adding a mathematical axiom.",
        )
    ],
    table="status2",
    refs=["PROOF_STATUS", "AXIOMS", "SCIENTIFIC_REPORT"],
)
page(
    "15 | The assumption ladder",
    [
        B(
            "The idea",
            "A guarantee at one level does not automatically validate the next. Correct algebra still needs a conforming implementation. A conforming implementation still needs appropriate sensor physics. Ecological fractions need representative references, meaningful categories and independent truth.",
        ),
        B(
            "What most limits biological interpretation",
            "The historical library’s physical scale and reference purity remain unresolved. Linear mixing and cross-sensor coefficient transfer must be appropriate at aligned support. Recorded cover categories do not independently establish material purity or annual biological change. Independent contemporaneous field fractions are the final missing evidence, not another synthetic model sweep.",
        ),
    ],
    fig=11,
    caption=C(
        "The successive evidence requirements from equations to field abundance.",
        "Only the mathematical level is supplied by proof; examples support parts of implementation.",
        "Plan new measurements at the level where evidence is missing.",
        "A complete proof build does not fill calibration, biological or field-truth gaps.",
    ),
    refs=["ASSUMPTIONS", "Pipeline.full_pipeline_conditional"],
)
page(
    "16 | What we learned",
    [
        B(
            "The mathematical core is coherent under explicit assumptions",
            "Fixed linear and appropriate affine transformations preserve ideal mixture weights. The same transformation must be used on targets and references, with compatible finite support. Nonlinear, fitted or masked stages do not inherit that conclusion automatically.",
        ),
        B(
            "Preservation forward is not recovery backward",
            "Band reduction can destroy the distinction among mixtures. The forward equation can remain valid while more than one composition produces the same observation. The proof makes that possibility exact rather than rhetorical.",
        ),
        B(
            "Reconstruction and prediction answer different questions",
            "FCLS/MESMA reconstruct spectra from allowed ingredients. Ridge learns a regularized fraction predictor. Good reconstruction and good prediction both differ from unique physical inversion. A unique fitted coefficient matrix is not a unique biological composition.",
        ),
        B(
            "Library representation is central",
            "The empirical matched15 and global-year controls limit favorable averages. More representative reference diversity, valid units, independent sensor observations and contemporaneous field fractions matter more than declaring an algebraic winner.",
        ),
        B(
            "What this effort delivered",
            "All 106 theorem declarations rebuild with standard foundations only. Thirteen conformance/audit tests reconnect selected mathematical calculations to actual Python paths. The report adds explanations and figures, not new theorems or scientific refits. The implementation discrepancies remain visible and queued for separate review.",
        ),
        B(
            "How to use the result",
            "For a scientific claim, ask which mathematical hypotheses apply, whether the actual execution meets them, and what independent sensor/biological evidence supports the interpretation. Keep sampled recognition, synthetic fraction prediction and field abundance separate.",
        ),
        B(
            "The final boundary",
            "The proof does not tell us that every abundance estimate is true. It tells us precisely what must be true for an abundance estimate to have the interpretation we give it.",
        ),
    ],
    refs=["CLAIMS", "PROOF_STATUS", "AUDIT", "SCIENTIFIC_REPORT"],
)
# Companion provenance and finite checks precede the closing scientific synthesis.
page(
    "Evidence guide: what was rebuilt and compared",
    [
        B(
            "A checked mathematical layer",
            "All eight Lean source modules and their complete root import were read and rebuilt. Every one of the 106 project theorem declarations appears in the axiom audit. The only dependencies are Lean’s standard foundations; no theorem assumes that calibration, field observations or biological labels are correct.",
        ),
        B(
            "A finite implementation bridge",
            "The table gives the nine Lean rational calculations compared with actual Python paths. Absolute tolerances are declared in the conformance tests; relative tolerance is zero for these comparisons. Four further tests expose axis inference, tiny-response normalization, median/clipping noncommutation and overlapping extraction windows.",
        ),
        B(
            "Where the underlying evidence lives",
            "The canonical 26-page scientific report is Separability, Identifiability and Abundance under output/pdf/researcher_evidence/. The formal proof-status matrix, assumptions, transformation map and implementation audit are under formal/. This report’s tables, Markdown and manifests preserve exact source paths, theorem names, filters and hashes without copying the original spectral library.",
        ),
    ],
    table="bridge",
    refs=["AXIOMS", "BRIDGE", "CONFORMANCE", "SCIENTIFIC_REPORT"],
)
PAGES.insert(-1, PAGES.pop())
