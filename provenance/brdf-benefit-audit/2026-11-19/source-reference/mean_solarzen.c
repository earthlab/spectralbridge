#include "mean_solarzen.h"
#include "local_solar.h"

double mean_solarzen(char *utm_numhem, double ux, double uy, int year, int doy)
{
	double l8_li_sz, s2_li_sz;


	// L8 modelled solar zenith
	l8_li_sz = Li_solarzen(l8_inclination, l8_Local_Time_at_Descending_Node, utm_numhem, ux, uy, year, doy);

	// S2 modelled solar zenith
	s2_li_sz = Li_solarzen(s2_inclination, s2_Local_Time_at_Descending_Node, utm_numhem, ux, uy, year, doy);

	return (l8_li_sz + s2_li_sz) / 2;
}

double Li_solarzen(double inclination, double Local_Time_at_Descending_Node, char *utm_numhem, double ux, double uy, int iYear, int mdoy1) 
{
	int utmzone;
	double lon, lat;
	double msz, msa;

	utmzone = atoi(utm_numhem);
	if (strstr(utm_numhem, "S") && uy > 0)  /* Sentinel 2 */ 
		uy -= 10000000;		/* accommodate GCTP */
	utm2lonlat(utmzone, ux, uy, &lon, &lat);

	// Li, Z., Zhang, H.K., Roy, D.P., Investigation of Sentinel-2 bidirectional reflectance hot-spot sensing conditions. IEEE Transactions on Geoscience and Remote Sensing. ​In press.	double Mlat_hours; /* mean latitudinal overpass time*/
	double Mlat_hours; /* mean latitudinal overpass time*/
	// double inclination = 98.62*PI/180;
	inclination = inclination*PI/180;
	// double Local_Time_at_Descending_Node = 10.5;
	Mlat_hours = Local_Time_at_Descending_Node-asin(tan(lat*PI/180)/tan(inclination))*180/PI/15;
	// printf("Mlat_hours%f %f\n", Mlat_hours, lat);

	int iMonth_gmt, iDay_gmt;
	double dHours_gmt, dMinutes_gmt, dSecondsint_gmt;
	getGMTtime(lon,mdoy1,Mlat_hours,
		&iDay_gmt,&dHours_gmt, &dMinutes_gmt, &dSecondsint_gmt);

	getDate(iDay_gmt,iYear,&iMonth_gmt,&iDay_gmt);

	SolarGeometry(iYear, iMonth_gmt, iDay_gmt,
		dHours_gmt, dMinutes_gmt, dSecondsint_gmt,
		lat, lon, &msa, &msz);

	return msz;
}
