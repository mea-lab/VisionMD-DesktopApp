import numpy as np
import scipy.signal as signal
from app.analysis.signal_analyzers.gait_step_width import foot_line_widths
from app.analysis.signal_analyzers.gait_segment_variability import combine_segment_variability
from app.analysis.signal_analyzers.gait_extended_features import ankle_lift_samples, extended_results, phase_time_samples, velocity
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
    def analyze(
        self, phases, strides, poses_3D, fps, return_details=False,
        spatial_scale=1.0,
    ) -> dict:
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
                spatial_scale=spatial_scale,
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
                spatial_scale=spatial_scale,
            )

        quality.update({
            "frame_interval_ms": 1000.0 / float(fps),
            "temporal_variability_precision": "limited by video event timing; interpolation does not establish subframe accuracy",
            "ankle_lift_reference": "camera vertical above interpolated same-side stance medians; not toe/sole clearance",
            "velocity_method": "segment-local quadratic derivative, approximately 0.2 second window",
        })
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
        spatial_scale=1.0,
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
        if len(lhs) == 0 or len(rhs) == 0:
            raise Exception(f'No gait events were detected by gait transformer to compute features. ' + 
                            f'Number of LHS events: {len(lhs)}. ' +
                            f'Number of LTF events: {len(ltf)}. ' + 
                            f'Number of RHS events: {len(rhs)}. ' + 
                            f'Number of RTF events: {len(rtf)}. '
                            )

        # --- 2) Temporal phases (in frames) ---
        
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

        duration_groups = (L_steptime, R_steptime)
        if any(np.any(values <= 0) or np.any(values > 3.0 * fps) for values in duration_groups):
            raise ValueError("Gait events produced a non-positive or implausibly long phase duration.")

        # Combine for overall
        all_steptimes = np.concatenate([L_steptime, R_steptime])

        # --- 3) Convert to seconds & compute temporal averages ---
        avg_steptime_left  = L_steptime.mean() / fps
        avg_steptime_right = R_steptime.mean() / fps

        avg_steptime = all_steptimes.mean() / fps
        cadence      = 60.0 / avg_steptime

        # --- 4) Ankle-contact spatial estimates (metres) ---
        kp = keypoints_3D[:, gait_phase_order_idx] / 1000.0
        kp[:, :, 1] *= -1.0
        lhs_idx = np.round(lhs).astype(int)
        rhs_idx = np.round(rhs).astype(int)
        synthgait = self._synthgait_spatial_features(kp, lhs_idx, rhs_idx, fps=fps)
        spatial_scale = float(spatial_scale)
        if not np.isfinite(spatial_scale) or spatial_scale <= 0:
            raise ValueError("Gait spatial calibration scale must be positive and finite.")
        synthgait["step_lengths"] *= spatial_scale
        synthgait["step_speeds"] *= spatial_scale
        sl_left = synthgait["step_lengths"][synthgait["step_sides"] == 6]
        sl_right = synthgait["step_lengths"][synthgait["step_sides"] == 3]
        speed_left = synthgait["step_speeds"][synthgait["step_sides"] == 6]
        speed_right = synthgait["step_speeds"][synthgait["step_sides"] == 3]
        avg_length = float((sl_left.mean() + sl_right.mean()) / 2)
        avg_velocity = float((speed_left.mean() + speed_right.mean()) / 2)

        results = {
            "Average step time":             float(avg_steptime),
            "Average step length":           avg_length,
            "Average velocity":              float(avg_velocity),
            "Average cadence":               float(cadence),
            "Average step time left":        float(avg_steptime_left),
            "Average step time right":       float(avg_steptime_right),
            "Average step length left":      float(sl_left.mean()),
            "Average step length right":     float(sl_right.mean()),
            # The correlation now measures bilateral coordination of the same
            # pelvis-centred wrist-forward signals used for arm-swing amplitude.
            # This replaces the legacy elbow/camera-depth correlation.
            "Arm swing correlation":         float(synthgait["arm_swing_correlation"]),
            # Ankle-derived spatial estimates and normalized posture/arm range.
            # Width uses opposite-foot progression-line geometry.
            "Step width":                     float(synthgait["step_widths"].mean()) if synthgait["step_widths"].size else float("nan"),
            "Stooped posture":                float(synthgait["stooped_posture"]),
            "Arm swing left":                 float(synthgait["left_arm_swing"]),
            "Arm swing right":                float(synthgait["right_arm_swing"]),
            "Arm swing":                      float(synthgait["arm_swing"]),
            "Step length variability":        float(self._sample_standard_deviation(synthgait["step_lengths"])),
            "Step width variability":         float(self._sample_standard_deviation(synthgait["step_widths"])),
            "Step speed variability":         float(self._sample_standard_deviation(synthgait["step_speeds"])),
            # This is a VisionMD addition rather than a SynthGait-19K label.
            # It is the RMS of the torso's detrended mediolateral excursion.
            # Robust P95-P5 range of detrended mediolateral displacement.
            "Torso medial-lateral trunk motion ROM": float(synthgait["torso_ml_range"]),
        }

        samples = {
            "step_time_left": np.asarray(L_steptime, dtype=float) / fps,
            "step_time_right": np.asarray(R_steptime, dtype=float) / fps,
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

        for key in ("step_lengths", "step_widths", "step_speeds"):
            sample_key = {"step_lengths": "synthgait_step_length", "step_widths": "step_width", "step_speeds": "step_speed"}[key]
            for side, ankle_index in (("left", 6), ("right", 3)):
                side_key = "step_width_sides" if key == "step_widths" else "step_sides"
                samples[f"{sample_key}_{side}"] = synthgait[key][synthgait[side_key] == ankle_index]
        samples.update(phase_time_samples(gait_event_dic, float(fps)))
        samples.update(ankle_lift_samples(kp, gait_event_dic, float(fps)))
        for key in ("arm_velocity_left", "arm_velocity_right", "torso_ml_velocity"):
            samples[key] = synthgait[key]
        results.update(extended_results(samples))

        return (results, samples) if return_samples else results

    @staticmethod
    def _synthgait_spatial_features(kp, lhs_idx, rhs_idx, fps=30.0):
        """Calculate ankle-based spatial estimates from a straight segment.

        The SynthGait-19K reference annotations use SMPL motion with a known
        forward axis.  VisionMD instead has camera-coordinate MeTRAbs poses, so
        for each already separated straight-walking segment we derive a local
        horizontal frame from net pelvis travel: ``forward`` follows the subject
        and ``lateral`` is its horizontal perpendicular. Length, posture and
        arm measures use that segment frame. Width instead uses each contacting
        ankle relative to its bracketing opposite-foot progression line. All
        spatial measures remain estimates in camera coordinates.

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
        event_positions, event_frames, event_sides = [], [], []
        previous_frame = None
        for frame, ankle_index in events:
            if frame == previous_frame:
                continue
            event_positions.append(kp[frame, ankle_index])
            event_frames.append(frame)
            event_sides.append(ankle_index)
            previous_frame = frame
        feet = np.asarray(event_positions, dtype=float)
        if len(feet) < 2:
            raise ValueError("Not enough distinct heel strikes for step width.")
        step_vectors = np.diff(feet, axis=0)
        step_durations = np.diff(np.asarray(event_frames, dtype=float))
        if np.any(step_durations <= 0):
            raise ValueError("Heel strikes must be strictly ordered for step-speed calculation.")
        step_lengths = np.abs(step_vectors @ forward)
        # GAITRite-style opposite-foot progression line, estimated from ankle
        # contacts rather than measured heel centres. Requires R-L-R or L-R-L.
        width_samples = foot_line_widths(
            lhs_idx, kp[lhs_idx, 6][:, [0, 2]],
            rhs_idx, kp[rhs_idx, 3][:, [0, 2]],
        )
        step_widths = width_samples["widths"]
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
        left_arm_range = float(np.percentile(left_wrist_forward, 95) - np.percentile(left_wrist_forward, 5)) / leg_length
        right_arm_range = float(np.percentile(right_wrist_forward, 95) - np.percentile(right_wrist_forward, 5)) / leg_length
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
        torso_ml_range = float(np.percentile(torso_ml_deviation, 95) - np.percentile(torso_ml_deviation, 5))

        return {
            "step_lengths": step_lengths,
            "step_widths": step_widths,
            "step_width_sides": width_samples["sides"],
            "step_speeds": step_speeds,
            "step_sides": np.asarray(event_sides[1:]),
            "arm_velocity_left": velocity(left_wrist_forward, float(fps)),
            "arm_velocity_right": velocity(right_wrist_forward, float(fps)),
            "torso_ml_velocity": velocity(torso_ml_deviation, float(fps)),
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

        def mean(name, required=True):
            values = combine(name)
            if not values.size:
                if not required:
                    return float("nan")
                raise ValueError(f"No samples available for {name}.")
            return float(values.mean())

        def sample_standard_deviation(name):
            # This method is static: there is deliberately no analyzer instance
            # here.  Calling through the class also makes pooled cached results
            # usable without constructing a second analyzer.
            return GaitSignalAnalyzer._sample_standard_deviation(combine(name))

        left_step, right_step = combine("step_time_left"), combine("step_time_right")
        left_length, right_length = combine("synthgait_step_length_left"), combine("synthgait_step_length_right")
        all_steps = np.concatenate([left_step, right_step])

        def weighted_mean(value_name, weight_name):
            values, weights = combine(value_name), combine(weight_name)
            if not values.size or values.size != weights.size or not np.any(weights > 0):
                return float(values.mean()) if values.size else float("nan")
            return float(np.average(values, weights=weights))

        pooled = {
            "Average step time": float(all_steps.mean()),
            "Average step length": float((left_length.mean() + right_length.mean()) / 2) if left_length.size and right_length.size else float("nan"),
            "Average velocity": float("nan"),
            "Average cadence": float(60.0 / all_steps.mean()),
            "Average step time left": float(left_step.mean()),
            "Average step time right": float(right_step.mean()),
            "Average step length left": float(left_length.mean()) if left_length.size else float("nan"),
            "Average step length right": float(right_length.mean()) if right_length.size else float("nan"),
            "Arm swing correlation": weighted_mean("arm_correlation", "arm_correlation_weight"),
        }
        # Keep this optional so historic cached analyses and narrow unit-test
        # fixtures remain readable. New gait analyses always provide these
        # arrays through ``_synthgait_spatial_features`` above.
        if any("step_width" in item for item in sample_sets):
            torso_deviation = combine("torso_ml_deviation")
            torso_ranges = combine("torso_ml_range")
            pooled.update({
                "Step width": mean("step_width", required=False),
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
                "Torso medial-lateral trunk motion ROM": float(np.percentile(torso_deviation, 95) - np.percentile(torso_deviation, 5)),
            })
        extra_keys = {key for item in sample_sets for key in item}
        pooled.update(extended_results({key: combine(key) for key in extra_keys}))
        # All diagnostic variability follows the same hierarchy; never pool
        # observations across segment means or weight longer segments more.
        for key, name, scale in (
            ("step_time", "Step time variability (ms; estimated)", 1000),
            ("synthgait_step_length", "Step length variability", 1),
            ("step_speed", "Step speed variability", 1),
            ("step_width", "Step width variability", 1),
        ):
            chunks = [{side: item.get(key + "_" + side, []) for side in ("left", "right")} for item in sample_sets]
            stats = combine_segment_variability(chunks, minimum_per_side=2)
            pooled[name] = stats["value"] * scale if stats["available"] else float("nan")
        return pooled
    # ------------------------------------------------------------------
    # --- END: Helper methods ---
    # ------------------------------------------------------------------
