import numpy as np
import scipy.signal as signal
from app.analysis.models.gait_transformer.gait_phase_kalman import gait_kalman_smoother, compute_phases, get_event_times
from app.analysis.signal_analyzers.base_signal_analyzer import BaseSignalAnalyzer


class GaitSignalAnalyzer(BaseSignalAnalyzer):
    """
    Base signal analyzer for all signals (hand movement, finger tap, leg agility, toe tapping, etc.)
    Each  subclass must implement these abstract methods for analyzing a signal
    """

    # ------------------------------------------------------------------
    # --- START: Abstract properties definitions
    # ------------------------------------------------------------------

    _metrabs_joint_order = np.array(['htop', 'neck', 'rsho', 'relb', 'rwri', 'lsho',
                            'lelb', 'lwri', 'rhip', 'rkne', 'rank', 'lhip', 
                            'lkne', 'lank', 'pelv', 'spin', 'head'])
    
    _gait_phase_joint_order = ['pelv', 'rhip', 'rkne', 'rank', 'lhip', 'lkne', 
                            'lank', 'spin', 'neck', 'head', 'htop', 'lsho', 
                            'lelb', 'lwri', 'rsho', 'relb', 'rwri']
    
    _gait_phase_order_idx = None

    # ------------------------------------------------------------------
    # --- End: Abstract properties definitions
    # ------------------------------------------------------------------





    # ------------------------------------------------------------------
    # --- START: Abstract methods ---
    # ------------------------------------------------------------------
    def analyze(self, phases, strides, poses_3D, fps, return_details=False) -> dict:
        if GaitSignalAnalyzer._gait_phase_order_idx is None:
            GaitSignalAnalyzer._gait_phase_order_idx = np.array(
                [self._metrabs_joint_order.tolist().index(j) for j in GaitSignalAnalyzer._gait_phase_joint_order]
            )
    
        phase_ordered = np.take(phases, [0, 4, 1, 5, 2, 6, 3, 7], axis=-1)
        state, _, _ = gait_kalman_smoother(phase_ordered)
        timestamps = np.arange(state.shape[0])
        raw_gait_event_dic = get_event_times(state, timestamps)
        gait_event_dic, quality = self.clean_gait_events(
            raw_gait_event_dic, poses_3D, GaitSignalAnalyzer._gait_phase_order_idx, fps
        )
        gait_event_dic, boundary_quality = self.discard_boundary_steps(gait_event_dic)
        quality.update(boundary_quality)

        try:
            results, samples = self.analyze_gait_video_features(
                gait_event_dic,
                poses_3D,
                GaitSignalAnalyzer._gait_phase_order_idx,
                fps,
                return_samples=True,
            )
        except (ValueError, IndexError):
            # Event validation is deliberately conservative.  If it leaves too
            # few events for a legacy feature, retain the old analysis rather
            # than turning a quality-control decision into a failed task.
            gait_event_dic = self._sanitize_event_dictionary(raw_gait_event_dic, len(poses_3D))
            gait_event_dic, boundary_quality = self.discard_boundary_steps(gait_event_dic)
            quality.update(boundary_quality)
            quality["used_cleaned_events"] = False
            quality["fallback_reason"] = "cleaned events were insufficient for feature calculation"
            results, samples = self.analyze_gait_video_features(
                gait_event_dic,
                poses_3D,
                GaitSignalAnalyzer._gait_phase_order_idx,
                fps,
                return_samples=True,
            )

        if return_details:
            return results, gait_event_dic, samples, quality
        return results, gait_event_dic


    # ------------------------------------------------------------------
    # --- END: Abstract methods ---
    # ------------------------------------------------------------------





    # ------------------------------------------------------------------
    # --- START: Helper methods ---
    # ------------------------------------------------------------------
    
    def analyze_gait_video_features(
        self,
        gait_event_dic: dict,
        keypoints_3D: np.ndarray,
        gait_phase_order_idx: list,
        fps,
        return_samples=False,
    ) -> dict:
        """
        Analyze spatiotemporal gait features from gait event timings and 3D keypoints.

        Parameters:
            gait_event_dic (dict): Must contain four keys—
                'left_down', 'left_up', 'right_down', 'right_up'—
                each mapping to a 1D numpy array of event-frame floats.
            keypoints_3D (np.ndarray): Array of shape (n_frames, n_keypoints, 3)
                containing raw 3D keypoint coordinates.
            gait_phase_order_idx (list): Permutation index to reorder the keypoints.
            fps (int): Frames per second of the video.

        Returns:
            dict: A dictionary of lists (length 1) of gait features.
        """

        # --- 1) Extract raw event arrays ---
        lhs = np.asarray(gait_event_dic['left_down'],   dtype=float)
        ltf = np.asarray(gait_event_dic['left_up'],     dtype=float)
        rhs = np.asarray(gait_event_dic['right_down'],  dtype=float)
        rtf = np.asarray(gait_event_dic['right_up'],    dtype=float)
        if len(lhs) == 0 or len(ltf) == 0 or len(rhs) == 0 or len(rtf) == 0:
            raise Exception(f'No gait events were detected by gait transformer to compute features. ' + 
                            f'Number of LHS events: {len(lhs)}. ' +
                            f'Number of LTF events: {len(ltf)}. ' + 
                            f'Number of RHS events: {len(rhs)}. ' + 
                            f'Number of RTF events: {len(rtf)}. '
                            )

        # --- 2) Temporal phases (in frames) ---
        
        # Calculate swing times
        if ltf[0] < lhs[0]:
            num_left_swings = min(len(ltf), len(lhs))
            L_swing  = lhs[0:num_left_swings] - ltf[0:num_left_swings]
        else:
            num_left_swings = min(len(ltf), len(lhs) - 1)
            L_swing  = lhs[1:num_left_swings + 1] - ltf[0:num_left_swings]
            
        if rtf[0] < rhs[0]:
            num_right_swings = min(len(rtf), len(rhs))
            R_swing  = rhs[0:num_right_swings] - rtf[0:num_right_swings]
        else:
            num_right_swings = min(len(rtf), len(rhs) - 1)
            R_swing  = rhs[1:num_right_swings + 1] - rtf[0:num_right_swings]
        if len(R_swing) == 0 or len(L_swing) == 0:
            raise ValueError("No right swing or left swing events were detected by gait transformer to compute features.")

        # Calculate stance times
        if lhs[0] < ltf[0]:
            num_left_stances = min(len(lhs), len(ltf))
            L_stance  = ltf[0:num_left_stances] - lhs[0:num_left_stances]
        else:
            num_left_stances = min(len(lhs), len(ltf) - 1)
            L_stance  = ltf[1:num_left_stances + 1] - lhs[0:num_left_stances]

        if rhs[0] < rtf[0]:
            num_right_stances = min(len(rhs), len(rtf))
            R_stance  = rtf[0:num_right_stances] - rhs[0:num_right_stances]
        else:
            num_right_stances = min(len(rhs), len(rtf) - 1)
            R_stance  = rtf[1:num_right_stances + 1] - rhs[0:num_right_stances]
        if len(R_stance) == 0 or len(L_stance) == 0:
            raise ValueError("No right stance or left stance events were detected by gait transformer to compute features.")

        # Calculate step times
        if rhs[0] < lhs[0]:
            num_left_steps = min(len(rhs), len(lhs))
            L_steptime = lhs[:num_left_steps] - rhs[:num_left_steps]
        else:
            num_left_steps = min(len(rhs), len(lhs) - 1)
            L_steptime = lhs[1:num_left_steps + 1] - rhs[:num_left_steps] 

        if lhs[0] < rhs[0]:
            num_right_steps = min(len(lhs), len(rhs))
            R_steptime = rhs[:num_right_steps] - lhs[:num_right_steps]
        else:
            num_right_steps = min(len(lhs), len(rhs) - 1)
            R_steptime = rhs[1:num_right_steps + 1] - lhs[:num_right_steps]
        if len(R_steptime) == 0 or len(L_steptime) == 0:
            raise ValueError("Not enough gait events were detected by gait transformer to compute right steptime or left steptime features.")

        # Calculate double support times
        if lhs[0] < rtf[0]:
            num_d1 = min(len(lhs), len(rtf))
            d1 = rtf[:num_d1] - lhs[:num_d1]
        else:
            num_d1 = min(len(lhs), len(rtf) - 1)
            d1 = rtf[1:1 + num_d1] - lhs[:num_d1]

        if rhs[0] < ltf[0]:
            num_d2 = min(len(rhs), len(ltf))
            d2 = ltf[:num_d2] - rhs[:num_d2]
        else:
            num_d2 = min(len(rhs), len(ltf) - 1)
            d2 = ltf[1:1 + num_d2] - rhs[:num_d2]
        d1_trimmed = d1[:min(len(d1), len(d2))]
        d2_trimmed = d2[:min(len(d1), len(d2))]
        if len(d1_trimmed) == 0 or len(d2_trimmed) == 0:
            raise ValueError("Not enough gait events were detected by gait transformer to compute the double support time feature.")

        duration_groups = (L_swing, R_swing, L_stance, R_stance, L_steptime, R_steptime)
        if any(np.any(values <= 0) or np.any(values > 3.0 * fps) for values in duration_groups):
            raise ValueError("Gait events produced a non-positive or implausibly long phase duration.")

        # Combine for overall
        all_swings    = np.concatenate([L_swing, R_swing])
        all_stances   = np.concatenate([L_stance, R_stance])
        all_steptimes = np.concatenate([L_steptime, R_steptime])
        all_double_support = (d1_trimmed + d2_trimmed)[~np.isnan(d1_trimmed + d2_trimmed)]

        # --- 3) Convert to seconds & compute temporal averages ---
        avg_swing_left   = L_swing.mean()    / fps
        avg_swing_right  = R_swing.mean()    / fps
        avg_stance_left  = L_stance.mean()   / fps
        avg_stance_right = R_stance.mean()   / fps
        avg_steptime_left  = L_steptime.mean() / fps
        avg_steptime_right = R_steptime.mean() / fps

        avg_swing    = all_swings.mean()    / fps
        avg_stance   = all_stances.mean()   / fps
        avg_steptime = all_steptimes.mean() / fps
        avg_double   = all_double_support.mean() / fps
        cadence      = 60.0 / avg_steptime

        # --- 4) Spatial metrics from hip Z (reorder, scale to meters, flip Y) ---
        kp = keypoints_3D[:, gait_phase_order_idx] / 1000.0 
        kp[:, :, 1] *= -1.0
        z_hip = kp[:, 0, 2]

        lhs_idx = np.round(lhs).astype(int)
        rhs_idx = np.round(rhs).astype(int)

        # step lengths per side
        if lhs[0] < rhs[0]:
            m = min(len(lhs_idx) - 1, len(rhs_idx))
            sl_left  = np.abs(z_hip[lhs_idx[1:m+1]] - z_hip[rhs_idx[:m]])
            sl_right = np.abs(z_hip[rhs_idx[:m]]    - z_hip[lhs_idx[:m]])
        else:
            m = min(len(lhs_idx), len(rhs_idx) - 1)
            sl_left  = np.abs(z_hip[lhs_idx[:m]]      - z_hip[rhs_idx[:m]])
            sl_right = np.abs(z_hip[rhs_idx[1:m+1]]   - z_hip[lhs_idx[:m]])

        if len(sl_left) == 0 or len(sl_right) == 0:
            raise ValueError("Not enough alternating heel strikes to calculate step length.")
        all_step_lengths = np.concatenate([sl_left, sl_right])
        strikes   = np.unique(np.sort(np.concatenate([lhs_idx, rhs_idx])))
        if len(strikes) < 2 or strikes[-1] == strikes[0]:
            raise ValueError("At least two distinct heel strikes are required to calculate velocity.")
        avg_velocity = np.abs((z_hip[strikes[-1]] - z_hip[strikes[0]]) / (strikes[-1] - strikes[0]) * fps)

        synthgait = self._synthgait_spatial_features(kp, lhs_idx, rhs_idx, fps=fps)

        results = {
            "Average stance time":           float(avg_stance),
            "Average swing time":            float(avg_swing),
            "Average double support time":   float(avg_double),
            "Average step time":             float(avg_steptime),
            "Average step length":           float(all_step_lengths.mean()),
            "Average velocity":              float(avg_velocity),
            "Average cadence":               float(cadence),
            "Average stance time left":      float(avg_stance_left),
            "Average stance time right":     float(avg_stance_right),
            "Average swing time left":       float(avg_swing_left),
            "Average swing time right":      float(avg_swing_right),
            "Average step time left":        float(avg_steptime_left),
            "Average step time right":       float(avg_steptime_right),
            "Average step length left":      float(sl_left.mean()),
            "Average step length right":     float(sl_right.mean()),
            # The correlation now measures bilateral coordination of the same
            # pelvis-centred wrist-forward signals used for arm-swing amplitude.
            # This replaces the legacy elbow/camera-depth correlation.
            "Arm swing correlation":         float(synthgait["arm_swing_correlation"]),
            # The four measures below follow the definitions in SynthGait-19K
            # (Mehraban et al., 2026).  The pre-existing VisionMD step-length
            # measure is intentionally retained for backward compatibility.
            "SynthGait step length":          float(synthgait["step_lengths"].mean()),
            "Step width":                     float(synthgait["step_widths"].mean()),
            "Stooped posture":                float(synthgait["stooped_posture"]),
            "Arm swing left":                 float(synthgait["left_arm_swing"]),
            "Arm swing right":                float(synthgait["right_arm_swing"]),
            "Arm swing":                      float(synthgait["arm_swing"]),
            "Step length variability":        float(self._sample_standard_deviation(synthgait["step_lengths"])),
            "Step width variability":         float(self._sample_standard_deviation(synthgait["step_widths"])),
            "Step speed variability":         float(self._sample_standard_deviation(synthgait["step_speeds"])),
            # This is a VisionMD addition rather than a SynthGait-19K label.
            # It is the RMS of the torso's detrended mediolateral excursion.
            "Torso medial-lateral displacement": float(synthgait["torso_ml_rms"]),
            "Torso medial-lateral displacement range": float(synthgait["torso_ml_range"]),
            # Explicit clinical label for the existing peak-to-peak lateral
            # trunk excursion. Keep the older range name for saved JSON
            # compatibility.
            "Torso medial-lateral trunk motion ROM": float(synthgait["torso_ml_range"]),
        }

        samples = {
            "stance_left": np.asarray(L_stance, dtype=float) / fps,
            "stance_right": np.asarray(R_stance, dtype=float) / fps,
            "swing_left": np.asarray(L_swing, dtype=float) / fps,
            "swing_right": np.asarray(R_swing, dtype=float) / fps,
            "step_time_left": np.asarray(L_steptime, dtype=float) / fps,
            "step_time_right": np.asarray(R_steptime, dtype=float) / fps,
            "double_support": np.asarray(all_double_support, dtype=float) / fps,
            "step_length_left": np.asarray(sl_left, dtype=float),
            "step_length_right": np.asarray(sl_right, dtype=float),
            "velocity": np.asarray([avg_velocity], dtype=float),
            "velocity_weight": np.asarray([(strikes[-1] - strikes[0]) / fps], dtype=float),
            "arm_correlation": np.asarray([synthgait["arm_swing_correlation"]], dtype=float),
            "arm_correlation_weight": np.asarray([len(keypoints_3D)], dtype=float),
            "synthgait_step_length": np.asarray(synthgait["step_lengths"], dtype=float),
            "step_width": np.asarray(synthgait["step_widths"], dtype=float),
            "step_speed": np.asarray(synthgait["step_speeds"], dtype=float),
            "stooped_posture": np.asarray([synthgait["stooped_posture"]], dtype=float),
            "stooped_posture_weight": np.asarray([len(keypoints_3D)], dtype=float),
            "arm_swing_left": np.asarray([synthgait["left_arm_swing"]], dtype=float),
            "arm_swing_right": np.asarray([synthgait["right_arm_swing"]], dtype=float),
            "arm_swing_weight": np.asarray([len(keypoints_3D)], dtype=float),
            "torso_ml_deviation": np.asarray(synthgait["torso_ml_deviation"], dtype=float),
            "torso_ml_range": np.asarray([synthgait["torso_ml_range"]], dtype=float),
        }

        return (results, samples) if return_samples else results

    @staticmethod
    def _synthgait_spatial_features(kp, lhs_idx, rhs_idx, fps=30.0):
        """Calculate paper-compatible spatial features from a straight segment.

        The SynthGait-19K reference annotations use SMPL motion with a known
        forward axis.  VisionMD instead has camera-coordinate MeTRAbs poses, so
        for each already separated straight-walking segment we derive a local
        horizontal frame from net pelvis travel: ``forward`` follows the subject
        and ``lateral`` is its horizontal perpendicular.  This lets away- and
        toward-camera passes contribute to the same summary without changing the
        published definitions.

        Joint indices refer to ``_gait_phase_joint_order`` after reordering:
        pelvis=0, right ankle=3, left ankle=6, neck=8, spine=7,
        left wrist=13, right wrist=16.
        """
        pelvis = kp[:, 0]
        strike_frames = np.unique(np.sort(np.concatenate([lhs_idx, rhs_idx])))
        if len(strike_frames) < 2:
            raise ValueError("At least two heel strikes are required for spatial gait features.")
        start, end = int(strike_frames[0]), int(strike_frames[-1])
        horizontal_travel = pelvis[end, [0, 2]] - pelvis[start, [0, 2]]
        norm = float(np.linalg.norm(horizontal_travel))
        if not np.isfinite(norm) or norm < 1e-6:
            # Preserve the established VisionMD behaviour for a nearly
            # stationary/noisy track. The comparison metrics become less
            # interpretable, but must not make an otherwise analyzable gait
            # task fail solely because no participant-relative axis is known.
            forward = np.array([0.0, 0.0, 1.0])
        else:
            forward = np.array([horizontal_travel[0] / norm, 0.0, horizontal_travel[1] / norm])
        lateral = np.array([-forward[2], 0.0, forward[0]])

        # A robust per-subject leg length keeps posture and arm swing
        # dimensionless, as in the paper. Median pooling avoids a single noisy
        # 3D frame changing the scale.
        right_leg = (
            np.linalg.norm(kp[:, 1] - kp[:, 2], axis=1)
            + np.linalg.norm(kp[:, 2] - kp[:, 3], axis=1)
        )
        left_leg = (
            np.linalg.norm(kp[:, 4] - kp[:, 5], axis=1)
            + np.linalg.norm(kp[:, 5] - kp[:, 6], axis=1)
        )
        leg_length = float(np.nanmedian(np.concatenate([right_leg, left_leg])))
        if not np.isfinite(leg_length) or leg_length <= 1e-6:
            # The fallback retains a finite, explicitly non-calibrated ratio
            # for malformed input rather than breaking legacy gait features.
            leg_length = 1.0

        # SynthGait uses the stepping foot's position at each successive heel
        # strike. ``discard_boundary_steps`` has already removed the first and
        # last heel strikes from the task before this function is called, so the
        # resulting vectors are the interior steps only. This avoids reporting
        # start-up and stopping behaviour as steady gait.
        events = [(int(frame), 6) for frame in lhs_idx] + [(int(frame), 3) for frame in rhs_idx]
        events.sort(key=lambda item: item[0])
        event_positions, event_frames = [], []
        previous_frame = None
        for frame, ankle_index in events:
            if frame == previous_frame:
                continue
            event_positions.append(kp[frame, ankle_index])
            event_frames.append(frame)
            previous_frame = frame
        feet = np.asarray(event_positions, dtype=float)
        if len(feet) < 2:
            raise ValueError("Not enough distinct heel strikes for step width.")
        step_vectors = np.diff(feet, axis=0)
        step_durations = np.diff(np.asarray(event_frames, dtype=float))
        if np.any(step_durations <= 0):
            raise ValueError("Heel strikes must be strictly ordered for step-speed calculation.")
        step_lengths = np.abs(step_vectors @ forward)
        step_widths = np.abs(step_vectors @ lateral)
        step_speeds = step_lengths / (step_durations / float(fps))

        # Equation 7--10: pelvis-centred wrist range and the forward neck--
        # pelvis offset, both normalized by leg length.
        analysis_start, analysis_end = event_frames[0], event_frames[-1]
        analysis_slice = slice(analysis_start, analysis_end + 1)
        neck_offset = kp[analysis_slice, 8] - pelvis[analysis_slice]
        stooped_posture = float(np.nanmean(neck_offset @ forward) / leg_length)
        centred_left_wrist = kp[analysis_slice, 13] - pelvis[analysis_slice]
        centred_right_wrist = kp[analysis_slice, 16] - pelvis[analysis_slice]
        left_wrist_forward = centred_left_wrist @ forward
        right_wrist_forward = centred_right_wrist @ forward
        left_arm_range = np.ptp(left_wrist_forward) / leg_length
        right_arm_range = np.ptp(right_wrist_forward) / leg_length
        arm_swing = float((left_arm_range + right_arm_range) / 2.0)
        if np.std(left_wrist_forward) <= 1e-9 or np.std(right_wrist_forward) <= 1e-9:
            arm_swing_correlation = np.nan
        else:
            arm_swing_correlation = float(np.corrcoef(left_wrist_forward, right_wrist_forward)[0, 1])

        # VisionMD-specific torso mediolateral displacement.  The torso centre
        # uses pelvis, spine, and neck; a linear drift is removed before RMS so
        # camera/track drift is not reported as side-to-side trunk motion.
        torso = np.mean(kp[analysis_slice, [0, 7, 8]], axis=1)
        torso_lateral = torso @ lateral
        frame_index = np.arange(len(torso_lateral), dtype=float)
        trend = np.polyval(np.polyfit(frame_index, torso_lateral, 1), frame_index)
        torso_ml_deviation = torso_lateral - trend
        torso_ml_rms = float(np.sqrt(np.mean(torso_ml_deviation ** 2)))
        torso_ml_range = float(np.ptp(torso_ml_deviation))

        return {
            "step_lengths": step_lengths,
            "step_widths": step_widths,
            "step_speeds": step_speeds,
            "stooped_posture": stooped_posture,
            "left_arm_swing": float(left_arm_range),
            "right_arm_swing": float(right_arm_range),
            "arm_swing": arm_swing,
            "arm_swing_correlation": arm_swing_correlation,
            "torso_ml_deviation": torso_ml_deviation,
            "torso_ml_rms": torso_ml_rms,
            "torso_ml_range": torso_ml_range,
            "leg_length": leg_length,
            "forward_axis": forward,
            "lateral_axis": lateral,
        }

    @staticmethod
    def _sample_standard_deviation(values):
        """Return the sample SD for a per-step measure, or NaN when unavailable."""
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]
        return np.nan if values.size < 2 else float(np.std(values, ddof=1))

    @staticmethod
    def discard_boundary_steps(gait_event_dic):
        """Drop the first and last detected heel strikes from feature analysis.

        Start and stopping steps commonly contain acceleration/deceleration and
        are not representative of steady gait. Only heel strikes are cropped:
        toe-off events are retained so the stance and swing interval matching
        remains valid for the retained heel strikes. Spatial, arm, and torso
        features use the resulting inner heel-strike interval. Very short
        recordings (fewer than five heel strikes) are preserved rather than
        failing an otherwise usable legacy analysis; the returned quality flag
        makes that exception explicit.
        """
        strikes = np.unique(np.sort(np.concatenate([
            np.asarray(gait_event_dic.get("left_down", []), dtype=float),
            np.asarray(gait_event_dic.get("right_down", []), dtype=float),
        ])))
        if strikes.size < 5:
            return gait_event_dic, {
                "boundary_steps_discarded": False,
                "boundary_step_discard_reason": "fewer than five heel strikes",
            }
        first_retained, last_retained = strikes[1], strikes[-2]
        trimmed = dict(gait_event_dic)
        for key in ("left_down", "right_down"):
            values = np.asarray(gait_event_dic.get(key, []), dtype=float)
            trimmed[key] = values[(values >= first_retained) & (values <= last_retained)]
        return trimmed, {
            "boundary_steps_discarded": True,
            "boundary_step_discard_reason": None,
            "discarded_first_heel_strike": float(strikes[0]),
            "discarded_last_heel_strike": float(strikes[-1]),
        }

    @staticmethod
    def _sanitize_event_dictionary(gait_event_dic, frame_count):
        cleaned = {}
        upper = max(0, int(frame_count) - 1)
        for key in ("left_down", "left_up", "right_down", "right_up"):
            values = np.asarray(gait_event_dic.get(key, []), dtype=float)
            values = values[np.isfinite(values)]
            cleaned[key] = np.unique(np.clip(values, 0, upper))
        return cleaned

    def clean_gait_events(self, gait_event_dic, poses_3D, gait_phase_order_idx, fps):
        """Reject impossible heel-strike sequences without deleting valid first steps.

        A candidate strike must alternate feet and be separated by a plausible
        step interval.  A small pelvis-displacement check suppresses rapid phase
        glitches while allowing walking in either camera direction.  If cleaning
        becomes too aggressive, :meth:`analyze` automatically falls back to the
        sanitized transformer events and records that decision in QC metadata.
        """
        events = self._sanitize_event_dictionary(gait_event_dic, len(poses_3D))
        raw_counts = {key: int(len(value)) for key, value in events.items()}
        merged = sorted(
            [(float(frame), "left") for frame in events["left_down"]]
            + [(float(frame), "right") for frame in events["right_down"]]
        )
        if not merged:
            return events, {
                "raw_event_counts": raw_counts,
                "cleaned_event_counts": raw_counts,
                "rejected_heel_strikes": 0,
                "used_cleaned_events": True,
                "fallback_reason": None,
            }

        kp = np.asarray(poses_3D, dtype=float)[:, gait_phase_order_idx] / 1000.0
        pelvis = kp[:, 0]
        min_step_frames = max(1.0, 0.20 * float(fps))
        max_step_frames = max(min_step_frames + 1.0, 2.0 * float(fps))
        accepted = [merged[0]]
        for frame, side in merged[1:]:
            previous_frame, previous_side = accepted[-1]
            interval = frame - previous_frame
            if side == previous_side or interval < min_step_frames or interval > max_step_frames:
                continue
            accepted.append((frame, side))

        # Very small alternating movements at the recording boundaries are
        # commonly preparatory foot lifts rather than walking steps.  Trim only
        # boundary events: an unusually short step in the middle is retained,
        # because pathological gait can contain genuine highly variable steps.
        progress = []
        for (first_frame, _), (second_frame, _) in zip(accepted[:-1], accepted[1:]):
            first_index = int(np.clip(round(first_frame), 0, len(pelvis) - 1))
            second_index = int(np.clip(round(second_frame), 0, len(pelvis) - 1))
            progress.append(abs(float(pelvis[second_index, 2] - pelvis[first_index, 2])))
        positive_progress = np.asarray([value for value in progress if np.isfinite(value) and value > 0])
        typical_progress = float(np.median(positive_progress)) if positive_progress.size else 0.0
        # Five percent of the subject's own median progression is deliberately
        # lenient.  The 1--5 cm bounds prevent numerical noise from setting the
        # cutoff while avoiding a normal-gait assumption for slow patients.
        boundary_progress_threshold = min(0.05, max(0.01, 0.05 * typical_progress))
        rejected_boundary_events = 0
        while len(accepted) > 4:
            first_frame = int(np.clip(round(accepted[0][0]), 0, len(pelvis) - 1))
            second_frame = int(np.clip(round(accepted[1][0]), 0, len(pelvis) - 1))
            if abs(float(pelvis[second_frame, 2] - pelvis[first_frame, 2])) >= boundary_progress_threshold:
                break
            accepted.pop(0)
            rejected_boundary_events += 1
        while len(accepted) > 4:
            first_frame = int(np.clip(round(accepted[-2][0]), 0, len(pelvis) - 1))
            second_frame = int(np.clip(round(accepted[-1][0]), 0, len(pelvis) - 1))
            if abs(float(pelvis[second_frame, 2] - pelvis[first_frame, 2])) >= boundary_progress_threshold:
                break
            accepted.pop()
            rejected_boundary_events += 1

        cleaned = dict(events)
        cleaned["left_down"] = np.asarray([f for f, s in accepted if s == "left"], dtype=float)
        cleaned["right_down"] = np.asarray([f for f, s in accepted if s == "right"], dtype=float)
        cleaned_counts = {key: int(len(value)) for key, value in cleaned.items()}
        quality = {
            "raw_event_counts": raw_counts,
            "cleaned_event_counts": cleaned_counts,
            "rejected_heel_strikes": int(len(merged) - len(accepted)),
            "rejected_boundary_heel_strikes": int(rejected_boundary_events),
            "boundary_progress_threshold_m": float(boundary_progress_threshold),
            "median_step_progression_m": float(typical_progress),
            "used_cleaned_events": True,
            "fallback_reason": None,
        }
        return cleaned, quality

    @staticmethod
    def pool_feature_samples(sample_sets):
        """Pool individual events across straight-walking segments.

        This is intentionally not an average of segment averages: a segment with
        ten valid steps contributes ten observations, while a segment with two
        steps contributes two.  Walking direction therefore has no effect on the
        primary results.
        """
        if not sample_sets:
            raise ValueError("No valid straight-walking segments were available.")

        def combine(name):
            arrays = [np.asarray(item.get(name, []), dtype=float) for item in sample_sets]
            arrays = [array[np.isfinite(array)] for array in arrays if array.size]
            return np.concatenate(arrays) if arrays else np.asarray([], dtype=float)

        def mean(name):
            values = combine(name)
            if not values.size:
                raise ValueError(f"No samples available for {name}.")
            return float(values.mean())

        def sample_standard_deviation(name):
            return self._sample_standard_deviation(combine(name))

        left_stance, right_stance = combine("stance_left"), combine("stance_right")
        left_swing, right_swing = combine("swing_left"), combine("swing_right")
        left_step, right_step = combine("step_time_left"), combine("step_time_right")
        left_length, right_length = combine("step_length_left"), combine("step_length_right")
        all_steps = np.concatenate([left_step, right_step])

        def weighted_mean(value_name, weight_name):
            values, weights = combine(value_name), combine(weight_name)
            if not values.size or values.size != weights.size or not np.any(weights > 0):
                return float(np.nanmean(values))
            return float(np.average(values, weights=weights))

        pooled = {
            "Average stance time": float(np.concatenate([left_stance, right_stance]).mean()),
            "Average swing time": float(np.concatenate([left_swing, right_swing]).mean()),
            "Average double support time": mean("double_support"),
            "Average step time": float(all_steps.mean()),
            "Average step length": float(np.concatenate([left_length, right_length]).mean()),
            "Average velocity": weighted_mean("velocity", "velocity_weight"),
            "Average cadence": float(60.0 / all_steps.mean()),
            "Average stance time left": float(left_stance.mean()),
            "Average stance time right": float(right_stance.mean()),
            "Average swing time left": float(left_swing.mean()),
            "Average swing time right": float(right_swing.mean()),
            "Average step time left": float(left_step.mean()),
            "Average step time right": float(right_step.mean()),
            "Average step length left": float(left_length.mean()),
            "Average step length right": float(right_length.mean()),
            "Arm swing correlation": weighted_mean("arm_correlation", "arm_correlation_weight"),
        }
        # Keep this optional so historic cached analyses and narrow unit-test
        # fixtures remain readable. New gait analyses always provide these
        # arrays through ``_synthgait_spatial_features`` above.
        if any("step_width" in item for item in sample_sets):
            torso_deviation = combine("torso_ml_deviation")
            torso_ranges = combine("torso_ml_range")
            pooled.update({
                "SynthGait step length": mean("synthgait_step_length"),
                "Step width": mean("step_width"),
                "Stooped posture": weighted_mean("stooped_posture", "stooped_posture_weight"),
                "Arm swing left": weighted_mean("arm_swing_left", "arm_swing_weight"),
                "Arm swing right": weighted_mean("arm_swing_right", "arm_swing_weight"),
                "Arm swing": float((
                    weighted_mean("arm_swing_left", "arm_swing_weight")
                    + weighted_mean("arm_swing_right", "arm_swing_weight")
                ) / 2.0),
                "Step length variability": sample_standard_deviation("synthgait_step_length"),
                "Step width variability": sample_standard_deviation("step_width"),
                "Step speed variability": sample_standard_deviation("step_speed"),
                "Torso medial-lateral displacement": float(np.sqrt(np.mean(torso_deviation ** 2))),
                "Torso medial-lateral displacement range": float(np.max(torso_ranges)),
                "Torso medial-lateral trunk motion ROM": float(np.max(torso_ranges)),
            })
        return pooled
    # ------------------------------------------------------------------
    # --- END: Helper methods ---
    # ------------------------------------------------------------------
