
#include "simulator.h"

static struct part *Part;

static void
findRMSandMaxForce(struct configuration *p, double *pRMS, double *pMaxForce)
{
  struct xyz f;
  int i;
  double forceSquared;
  double sum_forceSquared = 0.0;
  double max_forceSquared = -1.0;
  
  for (i=0; i<Part->num_atoms; i++) {
    f = ((struct xyz *)p->gradient)[i];
    forceSquared = vdot(f,f);
    sum_forceSquared += forceSquared;
    if (forceSquared > max_forceSquared) {
      max_forceSquared = forceSquared;
    }
  }
  *pRMS = sqrt(sum_forceSquared / Part->num_atoms);
  *pMaxForce = sqrt(max_forceSquared);
}

// This is the potential function which is being minimized.
static void
minimizeStructurePotential(struct configuration *p)
{
  updateVanDerWaals(Part, p, (struct xyz *)p->coordinate);
  p->functionValue = calculatePotential(Part, (struct xyz *)p->coordinate);
  //writeMinimizeMovieFrame(outf, Part, 0, (struct xyz *)p->coordinate, p->functionValue, p->parameter, Iteration++, "potential");
  //writeSimpleMovieFrame(Part, (struct xyz *)p->coordinate, NULL, "potential %e %e", p->functionValue, p->parameter);
}

// This is the gradient of the potential function which is being minimized.
static void
minimizeStructureGradient(struct configuration *p)
{
  int i;
  double rms_force;
  double max_force;
  
  updateVanDerWaals(Part, p, (struct xyz *)p->coordinate);
  calculateGradient(Part, (struct xyz *)p->coordinate, (struct xyz *)p->gradient);
  // dynamics wants gradient pointing downhill, we want it uphill
  for (i=0; i<3*Part->num_atoms; i++) {
    p->gradient[i] = -p->gradient[i];
  }
  findRMSandMaxForce(p, &rms_force, &max_force);
  //writeMinimizeMovieFrame(outf, Part, 0, (struct xyz *)p->coordinate, rms_force, max_force, Iteration++, "gradient");
  //writeSimpleMovieFrame(Part, (struct xyz *)p->coordinate, (struct xyz *)p->gradient, "gradient %e %e", rms_force, max_force);
  
}


static struct functionDefinition minimizeStructureFunctions;

void
minimizeStructure(struct part *part)
{
  int iter;
  struct configuration *initial;
  struct configuration *final;
  int i;
  int j;
  double rms_force;
  double max_force;
  
  Part = part;
    
  minimizeStructureFunctions.func = minimizeStructurePotential;
  minimizeStructureFunctions.dfunc = minimizeStructureGradient;
  minimizeStructureFunctions.freeExtra = NULL;
  minimizeStructureFunctions.coarse_tolerance = 1e-7;
  minimizeStructureFunctions.fine_tolerance = 1e-8;
  minimizeStructureFunctions.gradient_delta = 0.0; // unused
  minimizeStructureFunctions.dimension = part->num_atoms * 3;
  minimizeStructureFunctions.initial_parameter_guess = 0.00001;
  minimizeStructureFunctions.functionEvaluationCount = 0;
  minimizeStructureFunctions.gradientEvaluationCount = 0;

  initial = makeConfiguration(&minimizeStructureFunctions);
  for (i=0, j=0; i<part->num_atoms; i++) {
    initial->coordinate[j++] = part->positions[i].x;
    initial->coordinate[j++] = part->positions[i].y;
    initial->coordinate[j++] = part->positions[i].z;
  }

  final = minimize(initial, &iter, NumFrames * 100);

  evaluateGradient(final);
  findRMSandMaxForce(final, &rms_force, &max_force);
  
  writeMinimizeMovieFrame(outf, part, 1,
                          (struct xyz *)final->coordinate, rms_force, max_force, Iteration, "final structure");
  
  SetConfiguration(&initial, NULL);
  SetConfiguration(&final, NULL);
  doneExit(0, tracef, "Minimization final rms: %f, highForce: %f",
             rms_force, max_force);

}
