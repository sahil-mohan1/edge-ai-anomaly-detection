#ifndef CUSTOM_MODEL_H
#define CUSTOM_MODEL_H

#include <cmath>

// Logistic Regression Model for Leak Detection
class LeakDetectionModel {
public:
    // Standardization parameters (mean and std deviation)
    static constexpr float means[3] = {0.649487, 0.278802, 3.239087};
    static constexpr float stds[3] = {0.398183, 0.376616, 0.086358};

    // Logistic regression weights and bias
    static constexpr float weights[3] = {3.279568, -4.543833, -0.010264};
    static constexpr float bias = 0.843646;

    // Sigmoid function
    static float sigmoid(float x) {
        return 1.0f / (1.0f + exp(-x));
    }

    // Predict leak probability
    static float predict(float flow1, float flow2, float pressure) {
        // Standardize inputs
        float norm_flow1 = (flow1 - means[0]) / stds[0];
        float norm_flow2 = (flow2 - means[1]) / stds[1];
        float norm_pressure = (pressure - means[2]) / stds[2];

        // Compute linear combination (dot product)
        float linear_output = norm_flow1 * weights[0] + norm_flow2 * weights[1] + norm_pressure * weights[2] + bias;

        // Apply sigmoid activation
        return sigmoid(linear_output);
    }
};

enum CorrectionMode {
    MODE_AR = 0,
    MODE_DIURNAL = 1,
    MODE_HARMONIC = 2
};

// Water Level Anomaly Detector for sensor validation
class WaterLevelAnomalyDetector {
private:
    float last_corrected_wl = 1.34f;
    float prev_corrected_wl = 1.34f;
    CorrectionMode mode = MODE_AR;
    bool in_anomaly_seq = false;
    float anomaly_offset = 0.0f;
    bool prev_was_outage = false;

public:
    static constexpr float w_wl = -6.20248697f;
    static constexpr float w_ec = 0.32526515f;
    static constexpr float w_diff = 5.15647875f;
    static constexpr float bias = -1.4990f;

    // 2nd-order Autoregressive correction parameters
    static constexpr float w_ar1 = 1.61583692f;
    static constexpr float w_ar2 = -0.62776547f;
    static constexpr float bias_ar = 0.0276f;

    // Weekly Harmonic / Sinusoidal fit parameters
    static constexpr float harm_mean = 2.224497f;
    static constexpr float harm_c672 = -0.090816f;
    static constexpr float harm_s672 = -0.038300f;
    static constexpr float harm_c96  = 0.233601f;
    static constexpr float harm_s96  = 0.121749f;
    static constexpr float harm_c48  = -0.233784f;
    static constexpr float harm_s48  = -0.299686f;

    WaterLevelAnomalyDetector(CorrectionMode mode = MODE_AR) : mode(mode) {}

    void reset(float initial_wl = 1.34f) {
        last_corrected_wl = initial_wl;
        prev_corrected_wl = initial_wl;
        in_anomaly_seq = false;
        anomaly_offset = 0.0f;
        prev_was_outage = false;
    }

    float process_sample(float wl_raw, int errorcode, bool &is_anomaly, int bin = 0) {
        bool is_protocol_anomaly = (errorcode == 1 || errorcode == 3) || 
                                   (errorcode == 5 && (wl_raw == 0.0f || wl_raw >= 4.45f));
        bool is_bounds_anomaly = (wl_raw < 0.05f || wl_raw >= 4.45f);

        bool just_recovered = prev_was_outage && !is_protocol_anomaly && !is_bounds_anomaly;

        if (just_recovered) {
            is_anomaly = false;
            in_anomaly_seq = false;
            prev_corrected_wl = last_corrected_wl;
            last_corrected_wl = wl_raw;
            prev_was_outage = false;
            return wl_raw;
        }

        float abs_diff = std::abs(wl_raw - last_corrected_wl);
        bool is_roc_anomaly = (abs_diff > 0.6f);

        float z = w_wl * wl_raw + w_ec * (float)errorcode + w_diff * abs_diff + bias;
        bool is_logr_anomaly = (z > 0.0f);

        is_anomaly = is_protocol_anomaly || is_bounds_anomaly || is_roc_anomaly || is_logr_anomaly;

        if (!is_anomaly) {
            in_anomaly_seq = false;
            prev_corrected_wl = last_corrected_wl;
            last_corrected_wl = wl_raw;
            prev_was_outage = false;
            return last_corrected_wl;
        } else {
            float corrected;
            if (mode == MODE_DIURNAL) {
                static const float diurnal_profile[672] = {
                    2.927692f, 2.914545f, 2.848889f, 2.880000f, 2.845455f, 2.855833f, 2.950000f, 2.863846f,
                    2.849231f, 2.828333f, 2.850909f, 2.759167f, 2.713636f, 2.709167f, 2.686667f, 2.695833f,
                    2.692500f, 2.633333f, 2.588182f, 2.539167f, 2.610833f, 2.776364f, 3.022083f, 3.296500f,
                    3.199231f, 3.140750f, 3.215727f, 3.064538f, 3.028364f, 2.998231f, 2.967583f, 2.907308f,
                    2.865308f, 2.842083f, 2.759615f, 2.665615f, 2.577231f, 2.461538f, 2.320000f, 2.224692f,
                    2.189083f, 2.174273f, 2.146333f, 2.046538f, 2.047583f, 1.935231f, 1.953455f, 1.838923f,
                    1.788333f, 1.682308f, 1.621667f, 1.516154f, 1.441667f, 1.550769f, 1.406667f, 1.426923f,
                    1.453077f, 1.461538f, 1.495385f, 1.464615f, 1.506154f, 1.560000f, 1.480833f, 1.424615f,
                    1.454615f, 1.630833f, 1.957273f, 2.089167f, 2.198308f, 2.153846f, 2.074167f, 2.070000f,
                    1.834615f, 1.940833f, 2.035385f, 2.090833f, 2.033333f, 2.190833f, 2.012500f, 2.064615f,
                    1.904167f, 2.061538f, 2.061000f, 1.994615f, 1.865000f, 1.770000f, 1.997273f, 1.902308f,
                    1.707000f, 1.813636f, 2.063636f, 1.853077f, 1.847273f, 1.742500f, 1.820000f, 1.803846f,
                    1.713333f, 1.661111f, 1.764615f, 1.746154f, 1.842727f, 1.703077f, 1.724167f, 1.700000f,
                    1.605455f, 1.776364f, 1.506667f, 1.594615f, 1.569231f, 1.435000f, 1.522308f, 1.501538f,
                    1.559167f, 1.430000f, 1.525455f, 1.480000f, 1.540000f, 1.689286f, 2.477000f, 2.673444f,
                    2.272167f, 2.236083f, 2.309182f, 2.262727f, 2.069500f, 1.988385f, 1.958923f, 1.924846f,
                    1.876286f, 1.877714f, 1.855429f, 1.846154f, 1.809500f, 1.804786f, 1.859385f, 1.837500f,
                    1.883143f, 1.920308f, 1.903667f, 1.912417f, 1.822500f, 1.678333f, 1.660000f, 1.623077f,
                    1.597692f, 1.590769f, 1.567692f, 1.477143f, 1.454286f, 1.536923f, 1.575385f, 1.517857f,
                    1.521667f, 1.557692f, 1.550769f, 1.488571f, 1.505385f, 1.420769f, 1.453571f, 1.449231f,
                    1.471429f, 1.735385f, 1.958333f, 2.282308f, 2.453429f, 2.429077f, 2.520615f, 2.407500f,
                    2.392154f, 2.380000f, 2.272500f, 2.357692f, 2.307143f, 2.349167f, 2.343077f, 2.336154f,
                    2.240833f, 2.277273f, 2.312308f, 2.163077f, 2.359167f, 2.224286f, 2.158462f, 2.248462f,
                    2.231538f, 2.311667f, 2.237692f, 2.146429f, 2.223000f, 2.120714f, 2.261667f, 2.226667f,
                    2.227500f, 2.280000f, 2.031000f, 2.126154f, 2.070833f, 2.129167f, 2.047692f, 2.253636f,
                    2.058000f, 1.795385f, 1.972727f, 1.980000f, 2.040000f, 2.099091f, 1.792308f, 1.820000f,
                    1.938333f, 1.736429f, 1.575833f, 1.912500f, 1.889231f, 2.292500f, 2.331091f, 2.525545f,
                    2.393000f, 2.480545f, 2.634364f, 2.615083f, 2.650909f, 2.316083f, 2.221846f, 2.204077f,
                    2.179077f, 2.157769f, 2.192636f, 2.055154f, 1.982917f, 1.953231f, 1.946231f, 1.951231f,
                    1.976417f, 1.944385f, 1.922308f, 1.968333f, 1.890833f, 1.827273f, 1.822308f, 1.870000f,
                    1.835833f, 1.794286f, 1.739231f, 1.593571f, 1.503571f, 1.469286f, 1.446429f, 1.454286f,
                    1.495385f, 1.450714f, 1.435000f, 1.503846f, 1.434615f, 1.443846f, 1.449286f, 1.473571f,
                    1.597857f, 1.838462f, 2.148462f, 2.713333f, 2.711714f, 2.836700f, 2.670308f, 2.630833f,
                    2.564545f, 2.640909f, 2.575833f, 2.570000f, 2.568462f, 2.645833f, 2.567692f, 2.525455f,
                    2.568462f, 2.569167f, 2.561818f, 2.531818f, 2.560909f, 2.625000f, 2.529091f, 2.638182f,
                    2.528182f, 2.551667f, 2.550000f, 2.525000f, 2.518182f, 2.544167f, 2.540833f, 2.543333f,
                    2.544167f, 2.543333f, 2.522727f, 2.544167f, 2.544167f, 2.463636f, 2.525000f, 2.512727f,
                    2.540833f, 2.430000f, 2.540000f, 2.537500f, 2.507273f, 2.535833f, 2.532500f, 2.623000f,
                    2.527500f, 2.521667f, 2.520000f, 2.604000f, 2.610333f, 2.955909f, 3.129000f, 3.375417f,
                    3.440000f, 3.431273f, 3.472182f, 3.395417f, 3.448556f, 3.345091f, 3.375182f, 3.380333f,
                    3.371636f, 3.369727f, 3.366636f, 3.284000f, 3.293417f, 3.244250f, 3.172750f, 3.197000f,
                    3.050250f, 2.982091f, 2.982500f, 2.931083f, 2.902583f, 2.828167f, 2.712400f, 2.691100f,
                    2.352750f, 2.207273f, 2.060000f, 1.951538f, 1.881538f, 1.836923f, 1.756667f, 1.738333f,
                    1.645385f, 1.621538f, 1.583077f, 1.501667f, 1.518462f, 1.523846f, 1.518462f, 1.522308f,
                    1.705833f, 1.960000f, 2.299231f, 2.777692f, 3.123833f, 3.217923f, 3.176538f, 3.140909f,
                    2.999091f, 3.016667f, 3.027273f, 3.022308f, 2.932727f, 3.017273f, 2.883000f, 3.005385f,
                    3.002727f, 2.957000f, 2.987417f, 3.022417f, 2.960750f, 2.975385f, 3.002500f, 2.964615f,
                    3.017273f, 2.964083f, 2.950083f, 2.965000f, 2.969167f, 2.958818f, 2.922000f, 2.914000f,
                    2.874364f, 2.900727f, 2.776182f, 2.878273f, 2.874100f, 2.794545f, 2.827364f, 2.834455f,
                    2.843545f, 2.687273f, 2.731600f, 2.704778f, 2.656500f, 2.757778f, 2.514700f, 2.532000f,
                    2.532000f, 2.407000f, 2.398000f, 2.462000f, 2.451167f, 2.639500f, 2.932636f, 3.085750f,
                    3.157167f, 3.187833f, 3.059909f, 3.332900f, 3.032667f, 2.982083f, 2.915778f, 2.896417f,
                    2.847333f, 2.771583f, 2.793833f, 2.654000f, 2.637583f, 2.543333f, 2.400692f, 2.407500f,
                    2.339333f, 2.234077f, 2.141667f, 2.135385f, 2.133846f, 2.124615f, 2.146667f, 2.052727f,
                    2.045000f, 1.938462f, 1.887692f, 1.849231f, 1.788462f, 1.743846f, 1.716154f, 1.745385f,
                    1.703077f, 1.638462f, 1.631462f, 1.641077f, 1.511818f, 1.568750f, 1.440500f, 1.342615f,
                    1.481333f, 1.660077f, 1.866077f, 2.115000f, 2.239538f, 2.175000f, 2.091364f, 2.389556f,
                    2.251545f, 2.073818f, 2.067364f, 2.139083f, 2.119833f, 2.135222f, 1.932250f, 2.060700f,
                    2.014091f, 1.933917f, 2.078636f, 1.863143f, 1.935923f, 1.880200f, 2.065727f, 1.875727f,
                    1.850300f, 1.946700f, 1.867636f, 1.840231f, 1.883636f, 1.705000f, 1.887500f, 1.839091f,
                    1.588000f, 1.863333f, 1.970909f, 1.864444f, 1.726923f, 1.707692f, 1.666667f, 1.561667f,
                    1.634167f, 1.606923f, 1.586923f, 1.557692f, 1.445455f, 1.509231f, 1.488462f, 1.523333f,
                    1.452727f, 1.305000f, 1.470000f, 1.541818f, 1.471538f, 1.695583f, 1.993455f, 2.305400f,
                    2.154917f, 2.306400f, 1.970000f, 2.173909f, 1.940846f, 1.789455f, 1.880615f, 1.863083f,
                    1.927167f, 1.852833f, 1.853333f, 1.799750f, 1.754545f, 1.669750f, 1.655667f, 1.434545f,
                    1.550833f, 1.549091f, 1.432500f, 1.541000f, 1.407500f, 1.436364f, 1.372308f, 1.343846f,
                    1.302500f, 1.306154f, 1.303333f, 1.210000f, 1.241538f, 1.193077f, 1.071667f, 1.125385f,
                    1.100000f, 1.075000f, 1.065833f, 1.049167f, 1.042500f, 1.062500f, 1.054615f, 1.047692f,
                    1.154167f, 1.450000f, 1.838462f, 2.313636f, 2.465200f, 2.388091f, 2.342250f, 2.332333f,
                    2.397556f, 2.252800f, 2.264917f, 2.056364f, 2.258250f, 2.185364f, 2.255000f, 2.260818f,
                    2.189900f, 2.337900f, 2.360000f, 2.022222f, 2.258182f, 2.239100f, 2.343100f, 2.180100f,
                    2.255545f, 2.253727f, 2.289100f, 2.186100f, 2.303100f, 2.233727f, 2.303100f, 2.241909f,
                    2.244636f, 2.305100f, 2.244727f, 2.245455f, 2.283000f, 2.173000f, 2.262000f, 2.338714f,
                    2.228455f, 2.219091f, 2.295000f, 2.238000f, 2.239100f, 2.213909f, 2.214727f, 2.237900f,
                    2.293200f, 2.171333f, 2.245200f, 2.203818f, 2.336222f, 2.752500f, 3.049600f, 3.110300f,
                    2.972667f, 3.075600f, 2.981700f, 2.970500f, 3.031727f, 2.961833f, 2.875818f, 2.958833f,
                    2.947462f, 2.952000f, 2.873182f, 2.862250f, 2.790500f, 2.715917f, 2.661750f, 2.625909f,
                    2.551750f, 2.519182f, 2.444667f, 2.345500f, 2.228333f, 2.144167f, 2.115455f, 2.046154f,
                    2.000909f, 1.966923f, 1.911667f, 1.904615f, 1.919231f, 1.919231f, 1.896923f, 1.873846f,
                    1.853846f, 1.814167f, 1.834615f, 1.763846f, 1.772500f, 1.711429f, 1.755000f, 1.755000f,
                    1.933077f, 2.234615f, 2.503077f, 2.908083f, 3.261077f, 3.318538f, 3.275462f, 3.217000f,
                    3.204333f, 3.253182f, 3.228750f, 3.169000f, 3.084700f, 3.164000f, 3.159077f, 3.134667f,
                    3.075833f, 3.069833f, 3.056231f, 3.040000f, 3.010538f, 2.987750f, 2.977500f, 2.984154f,
                    2.937500f, 3.009800f, 2.955000f, 2.918333f, 2.952500f, 2.943846f, 2.940769f, 2.930769f,
                };
                if (!in_anomaly_seq) {
                    in_anomaly_seq = true;
                    int last_bin = (bin - 1 + 672) % 672;
                    anomaly_offset = last_corrected_wl - diurnal_profile[last_bin];
                }
                corrected = diurnal_profile[bin] + anomaly_offset;
            } else if (mode == MODE_HARMONIC) {
                if (!in_anomaly_seq) {
                    in_anomaly_seq = true;
                    int last_bin = (bin - 1 + 672) % 672;
                    float last_angle672 = 2.0f * 3.1415926535f * last_bin / 672.0f;
                    float last_angle96 = 2.0f * 3.1415926535f * last_bin / 96.0f;
                    float last_angle48 = 2.0f * 3.1415926535f * last_bin / 48.0f;
                    float last_pred = harm_mean + harm_c672 * std::cos(last_angle672) + harm_s672 * std::sin(last_angle672)
                                                + harm_c96  * std::cos(last_angle96)  + harm_s96  * std::sin(last_angle96)
                                                + harm_c48  * std::cos(last_angle48)  + harm_s48  * std::sin(last_angle48);
                    anomaly_offset = last_corrected_wl - last_pred;
                }
                float angle672 = 2.0f * 3.1415926535f * bin / 672.0f;
                float angle96 = 2.0f * 3.1415926535f * bin / 96.0f;
                float angle48 = 2.0f * 3.1415926535f * bin / 48.0f;
                float base_pred = harm_mean + harm_c672 * std::cos(angle672) + harm_s672 * std::sin(angle672)
                                            + harm_c96  * std::cos(angle96)  + harm_s96  * std::sin(angle96)
                                            + harm_c48  * std::cos(angle48)  + harm_s48  * std::sin(angle48);
                corrected = base_pred + anomaly_offset;
            } else { // MODE_AR
                corrected = w_ar1 * last_corrected_wl + w_ar2 * prev_corrected_wl + bias_ar;
            }
            prev_corrected_wl = last_corrected_wl;
            last_corrected_wl = corrected;
            prev_was_outage = is_protocol_anomaly || is_bounds_anomaly;
            return last_corrected_wl;
        }
    }
};

#endif // CUSTOM_MODEL_H
