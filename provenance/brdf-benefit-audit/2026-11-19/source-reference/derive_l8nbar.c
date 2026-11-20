/* Adjust the directional Landsat surface reflectance for nadir view and the mean solar 
 * zenith at the tile center for the respective time that Landsat and Sentinel-2 overpass
 * the tile-center latitude on the given day of the year.
 * For very high latitude, there is a chance that the desired solar zenith can't be derived
 * and the mean observed solar zenith for the Landsat data is used instead.
 *
 * Save output as HDF-EOS, and save the c-factor in a separate hdf.
 *
 * Mar 31, 2020: Recalculate the mean solar and view angles metadata. 
 * 		 Use band 5 (NIR) for view angles.
 * July 6, 2020: All bands have the same angle data now.
 *
#################### Credit -- Text from David Roy's group:
#  ! The modeled solar zenith for HLS NBAR (v1.5) is defined as a function of latitude and day of
#  ! the year (Li et al. 2019), and is calculated through a sensor overpass time model
#  ! (Eq. 4 in Li et al. 2019).  The purpose of this definition is to resembling the observed
#  ! solar zeniths (Zhang et al. 2016) as the c-factor approach (Roy et al. 2016) used in HLS
#  ! NBAR derivation is for viewing zenith correction and does not allow solar zenith extrapolation.
#  ! Note that the local overpass time at the Equator and the satellite inclination angle used in
#  ! the sensor overpass time model (Eq. 4 in Li et al. 2019) take the average of the values for
#  ! Landsat-8 and Sentinel-2.
#
#  ! Li, Z., Zhang, H.K., Roy, D.P., 2019. Investigation of Sentinel-2 bidirectional reflectance
#  ! hot-spot sensing conditions. IEEE Transactions on Geoscience and Remote Sensing, 57(6), 3591-3598.
#  !
#  ! Roy, D.P., Zhang, H. K., Ju, J., Gomez-Dans, J. L., Lewis, P.E., Schaaf C.B., Sun, Q., Li, J.,
#  ! Huang, H., Kovalskyy, V., 2016. A general method to normalize Landsat reflectance data to nadir
#  ! BRDF adjusted reflectance. Remote Sensing of Environment, 176, 255-271.
#  !
#  ! Zhang, H. K., Roy, D.P., Kovalskyy, V., 2016. Optimal solar geometry definition for global
#  ! long term Landsat time series bi-directional reflectance normalization. IEEE Transactions
#  ! on Geoscience and Remote Sensing, 54(3), 1410-1418.
################################################################################

 */

#include "hls_commondef.h"
#include "lsat.h"
#include "lsatmeta.h"
#include "l8ang.h"
#include "modis_brdf_coeff.h"
#include "rtls.h"
#include "cfactor.h"
#include "mean_solarzen.h"
#include "util.h"
#include "hls_hdfeos.h"

int main(int argc, char *argv[])
{
	/* Command line parameters */
	char fname_in[LINELEN]; 	/* Both input and output; open for update */ 
	char fname_ang[LINELEN];
	char fname_cfactor[LINELEN];

	l8ang_t l8ang;	/* 30-m angles */
	lsat_t lsatin;		/* Input and output reflectance */
	cfactor_t cfactor;	/* output BRDF ancillary; cfactor for each band */

	int ib, irow, icol, k; 

	double sz, sa, vz, va, ra;

	/* mean angles as metadata */
	double msz, msa, mvz, mva;
	int n;
	msz = msa = mvz = mva = 0;
	n = 0;

	double nbarsz;		/* solar zenith for NBAR*/
	double rossthick_nbarsz, lisparseR_nbarsz;	/* kernels at nadir view and the mean solar zenith */
	double ratio;
	double tmpref;
	double cenlon, cenlat;
	char creationtime[100];

	int utmzone;
	double cenx, ceny;

	int ret;

	if (argc != 4) {
		fprintf(stderr, "Usage: %s insr.hdf ang.hdf cfactor.hdf \n", argv[0]);
		exit(1);
	}

	strcpy(fname_in,      argv[1]);
	strcpy(fname_ang,     argv[2]);
	strcpy(fname_cfactor, argv[3]);

	/* Open input for update and save as output */
	strcpy(lsatin.fname, fname_in);
	ret = open_lsat(&lsatin, DFACC_WRITE);
	if (ret != 0) {
		Error("Error in open_lsat");	
		exit(1);
	}

	/* Read angles */
	strcpy(l8ang.fname, fname_ang);
	ret = open_l8ang(&l8ang, DFACC_READ);
	if (ret != 0) {
		Error("Error in open_l8ang");	
		exit(1);
	}
	
	/* Create the brdf ancillary file */
	strcpy(cfactor.fname, fname_cfactor);
	cfactor.nrow = lsatin.nrow;
	cfactor.ncol = lsatin.ncol;
	ret = open_cfactor(LANDSAT8, &cfactor, DFACC_CREATE);
	if (ret != 0) {
		Error("Error in open_cfactor");
		exit(1);
	}

	/* Calculate the mean solar zenith and solar azimuth in the tile for two uses:
	 *  1) After the Landsat sun/view angle is gridded from a scene into a tile, the 
	 *     scene-level mean sun/view angle metadata value loses its original meaning;
	 *     recalculate for the tile. 
	 *  2) For very high latitude, the recalculated mean solar zenith will also be used 
	 *     for NBAR since an "ideal" NBAR solar zenith according to David Roy can't be 
	 *     derived.
	 */
	for (irow = 0; irow < lsatin.nrow; irow++) {
		for (icol = 0; icol < lsatin.ncol; icol++) {
			k = irow * lsatin.ncol + icol;
			if (lsatin.ref[0][k] == HLS_REFL_FILLVAL)	/* Checking on any band is fine */
				continue;

			if (l8ang.sz[k] == ANGFILL || l8ang.sa[k] == ANGFILL ||
			    l8ang.vz[k] == ANGFILL || l8ang.va[k] == ANGFILL)
				continue;

			sz = l8ang.sz[k]/100.0;
			sa = l8ang.sa[k]/100.0;
			vz = l8ang.vz[k]/100.0;
			va = l8ang.va[k]/100.0;

			n++;
                        msz = msz + (sz-msz)/n;
                        msa = msa + (sa-msa)/n;
                        mvz = mvz + (vz-mvz)/n;
                        mva = mva + (va-mva)/n;
		}	
	}

	/*** Derive solar zenith to be used in BRDF adjustment. 
	 *
	 * Sentinel-2 nadir does not go higher than 81.38 deg and Landsat does not go 
	 * higher than 81.8.
	 * Compute the tile center latitude rather than reading it from a file. 
	 */
	utmzone = atoi(lsatin.zonehem);
	cenx = lsatin.ulx + (lsatin.ncol/2.0 * HLS_PIXSZ),
	ceny = lsatin.uly - (lsatin.nrow/2.0 * HLS_PIXSZ);
	if (strstr(lsatin.zonehem, "S") && ceny > 0)  /* Sentinel 2 */ 
		ceny -= 1E7;		/* accommodate GCTP */
	utm2lonlat(utmzone, cenx, ceny, &cenlon, &cenlat);

	if (cenlat > 81.3) 	/* The mean solar zenith of Sentinel-2 and Landsat can't be derived. */
		nbarsz = msz;
	else {
		/* Solar zenith to be used in BRDF adjustment. */
		/* Example basename of filename: HLS.L30.T03VXH.2019202.v1.4.hdf */
		char *cp;	
		int yeardoy, year, doy;
		cp = strrchr(lsatin.fname, '/');	/* find basename */
		if (cp == NULL)
			cp = lsatin.fname;
		else
			cp++;
		/* Skip to yeardoy */
		cp = strchr(cp, '.'); cp++;
		cp = strchr(cp, '.'); cp++;
		cp = strchr(cp, '.'); cp++;
		yeardoy = atoi(cp);
		year = yeardoy / 1000;
		doy = yeardoy - year * 1000;
	
		nbarsz = mean_solarzen(lsatin.zonehem, 
				    lsatin.ulx+(lsatin.ncol/2.0 * HLS_PIXSZ),
				    lsatin.uly-(lsatin.nrow/2.0 * HLS_PIXSZ),
				    year,
				    doy);
	}

	/* Update processing time */
	getcurrenttime(creationtime);
	SDsetattr(lsatin.sd_id, "HLS_PROCESSING_TIME", DFNT_CHAR8, strlen(creationtime), (VOIDP)creationtime);

	/* Spatial and cloud cover */
	lsat_setcoverage(&lsatin);

	rossthick_nbarsz = RossThick(nbarsz, 0, 0);
	lisparseR_nbarsz = LiSparseR(nbarsz, 0, 0); 

	/* The index of a band in the BRDF coefficient array */
	int specidx = -1;

	/* The input granule definitely has reflectance data.  If not, this tiled data
	 * wouldn't appear here for BRDF correction. This flag has been used in tiling. 
	 * Remember to set; otherwise the file will be deleted after closing*/
	lsatin.tile_has_data = 1;	

	for (ib = 0; ib < L8NRB-1; ib++) {
		/* ib = L8NRB-1 corresponds to cirrus; ignored.  */
		specidx = -1; 
		switch (ib) {
			case 0:  specidx =  0; break;   /* ultra-blue */
			case 1:  specidx =  0; break;	/* blue */
			case 2:  specidx =  1; break;	/* green */
			case 3:  specidx =  2; break;	/* red */
			/* Skip the 3 rows intended for the Sentinel-2 red-edge bands. Aug 8, 2019 */
			case 4:  specidx =  6; break;	/* nir */
			case 5:  specidx =  7; break;	/* swir 1. */
			case 6:  specidx =  8; break;	/* swir 2 */
		}
		if (specidx == -1) {
			Error("Something wrong with spectral band match between Landsat and MODIS");
			exit(1);
		}

		/* NBAR */
		for (irow = 0; irow < lsatin.nrow; irow++) {
			for (icol = 0; icol < lsatin.ncol; icol++) {
				k = irow * lsatin.ncol + icol;
				if (lsatin.ref[ib][k] == HLS_REFL_FILLVAL)
					continue;

				/* July 6, 2020. By any chance that the angle data is missing. Shouldn't happen
				 * now; just check.
				 */
				if (l8ang.sz[k] == ANGFILL) {
					lsatin.ref[ib][k] = HLS_REFL_FILLVAL;
					
					/* The same pixel location is reset repeatedly and wastefully, but it's ok */
					lsatin.ref[7][k] = HLS_REFL_FILLVAL; /* Cirrus */
					lsatin.thm[0][k] = HLS_THM_FILLVAL; /* TIRS 1 */
					lsatin.thm[1][k] = HLS_THM_FILLVAL; /* TIRS 2 */
					lsatin.acmask[k] = HLS_MASK_FILLVAL;
					lsatin.fmask[k]  = HLS_MASK_FILLVAL; 
				}
				else {
					sz = l8ang.sz[k]/100.0;
					sa = l8ang.sa[k]/100.0;
					vz = l8ang.vz[k]/100.0;
					va = l8ang.va[k]/100.0;

					ra = sa - va;

					ratio = (coeff[specidx][0] + coeff[specidx][1] * rossthick_nbarsz + coeff[specidx][2] * lisparseR_nbarsz) / 
						(coeff[specidx][0] + coeff[specidx][1] * RossThick(sz, vz, ra) + coeff[specidx][2] * LiSparseR(sz, vz, ra));
					tmpref = lsatin.ref[ib][k] * ratio;
					lsatin.ref[ib][k] = asInt16(tmpref);

					cfactor.ratio[ib][k] = ratio;
				}
			}
		}
	}

	close_l8ang(&l8ang);

	/* A few angle metadata items */
	write_nbar_solarzenith(&lsatin, nbarsz);
	write_mean_angle(&lsatin, msz, msa, mvz, mva);
	fprintf(stderr, "%lf %lf %lf %lf\n", msz, msa, mvz, mva);

	/* Close reflectance*/
	ret = close_lsat(&lsatin);
	if (ret != 0) {
		Error("Error in close_lsat");
		exit(1);
	}

	/* Close cfactor */
	ret = close_cfactor(&cfactor);
	if (ret != 0) {
		Error("Error in close_cfactor");
		exit(1);
	}

	/* Make it hdfeos */
        sds_info_t all_sds[L8NRB+L8NTB+2];  /* ref + therm + 2 QA */
        ret = set_L30_sds_info(all_sds, L8NRB+L8NTB+2, &lsatin);
	if (ret != 0) {
		Error("Error in set_L30_sds_info");
		exit(1);
	}
        ret = L30_PutSpaceDefHDF(lsatin.fname, all_sds, L8NRB+L8NTB+2);
        if (ret != 0) {
                Error("Error in HLS_PutSpaceDefHDF");
                exit(1);
        }

	return 0;
}
