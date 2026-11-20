#include "rtls.h"

#define MIN(a, b) ((a) < (b) ? (a) : (b)) 
#define MAX(a, b) ((a) > (b) ? (a) : (b)) 

double RossThick(double sz_deg, double vz_deg, double ra_deg)
{
	double thes, thev, phi;
	double cos_ksi, sin_ksi, ksi;
	double kernel;

	thes = sz_deg * deg2rad;
	thev = vz_deg * deg2rad;
	phi  = ra_deg * deg2rad;
	
	cos_ksi = cos(thes) * cos(thev) + sin(thes) * sin(thev) * cos(phi);
	sin_ksi = sqrt(1 - pow(cos_ksi, 2));
	ksi = acos(cos_ksi);

	kernel = ((pi/2 - ksi) * cos_ksi + sin_ksi)
		/ (cos(thes) + cos(thev)) - pi/4; 
	
	return kernel;
}

double LiSparseR(double sz_deg, double vz_deg, double ra_deg)
{
	double coef = 2;
	double thes, thev, phi;
	double delta, sec_thes, sec_thev;
	double M2I_sec, cos_t, sin_t, t, cos_ksi, temp, kernel;


	thes = sz_deg * deg2rad;
	thev = vz_deg * deg2rad;
	phi  = ra_deg * deg2rad;

	delta = sqrt(pow(tan(thes), 2) + pow(tan(thev), 2) - 2.0 * tan(thes) * tan(thev) * cos(phi));
	sec_thes = 1 / cos(thes);
	sec_thev = 1 / cos(thev);
	M2I_sec = sec_thes + sec_thev;
	cos_t = MAX(MIN(coef * sqrt(pow(delta,2) + pow(tan(thes) * tan(thev) * sin(phi), 2)) / M2I_sec, 1), -1);
	sin_t = sqrt(1 - pow(cos_t, 2));
	t = acos(cos_t);
	cos_ksi = cos(thes) * cos(thev) + sin(thes) * sin(thev) * cos(phi);  
	temp = (t - sin_t * cos_t) * M2I_sec / pi - M2I_sec;
	kernel = temp + (1 + cos_ksi) * sec_thev * sec_thes / 2; 

	return kernel;
}
