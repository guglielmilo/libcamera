/* SPDX-License-Identifier: LGPL-2.1-or-later */
/*
 * Copyright (C) 2019, Google Inc.
 *
 * logging.h - Logging infrastructure
 */

#pragma once

#include <functional>

namespace libcamera {

enum LoggingTarget {
	LoggingTargetNone,
	LoggingTargetSyslog,
	LoggingTargetFile,
	LoggingTargetStream,
	LoggingTargetCallback,
};

enum LogSeverity {
	LogInvalid = -1,
	LogDebug = 0,
	LogInfo,
	LogWarning,
	LogError,
	LogFatal,
};

int logSetFile(const char *path, bool color = false);
int logSetStream(std::ostream *stream, bool color = false);
int logSetTarget(LoggingTarget target);
int logSetCallback(std::function<void(LogSeverity, const std::string&)> callback);
void logSetLevel(const char *category, const char *level);

} /* namespace libcamera */
