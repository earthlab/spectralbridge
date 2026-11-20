#ifndef RTLS_H
#define RTLS_H

#include <math.h>
#include <stdlib.h>

#ifndef pi	/* GCTP uses PI */
#define pi 3.141592653589 
#endif

#define deg2rad (pi/180)

double RossThick(double sz_deg, double vz_deg, double ra_deg);
double LiSparseR(double sz_deg, double vz_deg, double ra_deg);

#endif
