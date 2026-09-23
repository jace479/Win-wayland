// SPDX-License-Identifier: LGPL-2.0-or-later
#pragma once

#include <QtCore/qglobal.h>

#ifndef DISCOVERCOMMON_EXPORT
#  if defined(DiscoverCommon_EXPORTS)
#    define DISCOVERCOMMON_EXPORT Q_DECL_EXPORT
#  else
#    define DISCOVERCOMMON_EXPORT Q_DECL_IMPORT
#  endif
#endif
