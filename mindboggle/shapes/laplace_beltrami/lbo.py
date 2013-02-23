#!/usr/bin/python
"""
Computing the Laplace-Beltrami Spectrum of a given structure. 

1. Geometric Laplacians (Desburn et al.'s, using cotangent kernel and area-based masses) 
2. FEM Laplacians (linear FEM version. Cubic FEM version later.)

We follow the definitions and steps given in Reuter et al.'s
Discrete Laplace-Beltrami Operators for Shape Analysis and Segmentation (2009)

Since Reuter et al. (2009) did not give explicit equations/algorithm to compute 
FEM Laplacian, Forrest derived the computation steps according to the paper.
No mathematician has verified his steps. 
And, this is free software. So, use at your own risk.   

The information about using SciPy to solve generalized eigenvalue problem is
at: http://docs.scipy.org/doc/scipy/reference/tutorial/arpack.html

Requires Scipy 0.10 or later to solve generalized eigenvalue problem. 

I just realize that PEP 8 says Capitalized_Letters_with_Underscores look UGLY!
This is contrary to what I remembered before. 
So I am replacing variable names gradually.  

Known things that you need to pay attention (not to be considered as bugs):
1. In ``nodes``, do NOT provide coordinates of vertices that do NOT appear on 
the 3-D structure whose LBS is to be calculated. 
For example, do not use coordinates of all POINTS from a VTK file as ``nodes`` 
and some of the faces (e.g., sulcus fold) as ``faces``. 
This will cause singular matrix error when inverting matrixes because some rows 
are all zeros. 

Acknowledgments:
    - Dr. Martin Reuter, MIT, http://reuter.mit.edu/ 
    - Dr. Eric You Xu, Google, http://www.youxu.info/

Authors:
    - Forrest Sheng Bao, 2012-2013  (forrest.bao@gmail.com)  http://fsbao.net
    - Eliezer Stavsky, 2012  (eli.stavsky@gmail.com)

Copyright 2013,  Mindboggle team (http://mindboggle.info), Apache v2.0 License
"""

def gen_V(Meshes, W, Neighbor):
    """Computer V as in Reuter et al.'s paper
    
    Parameters
    -------------
    Meshes : 2-D numpy array
        Meshes[i] is a 3-element array containing the indexes of nodes
    W: 2-D numpy array
        W[i,j] is w_{ij} in Eq. (3) of Reuter's paper
    v: a 1-D list
        v_i = \sum_{j\in N(i)} w_{ij} and N(i) is the set of neighbors of node i.
    Neighbor: a 2-D list
        Neighbor[i] gives the list of neighbors of node i on the mesh, in node indexes. 
        
    Returns 
    ----------
    V : a sparse diagnonal matrix
        As described in Reuter's paper
    
    """
    from scipy.sparse import lil_matrix
    num_nodes = W.shape[0]
    V=lil_matrix((num_nodes, num_nodes))
    v = [sum([W[i,j] for j in Neighbor[i]]) for i in range(num_nodes)]
    V.setdiag(v)
    return V/3

def area(Nodes, Meshes):
    """Compute the areas all triangles on the mesh

    Parameters
    -------------
    
    Nodes : 2-D numpy array 
        Nodes[i] is the 3-D coordinates of nodes on a mesh 
    Meshes : 2-D numpy array
        Meshes[i] is a 3-element array containing the indexes of nodes 
    
    Returns
    --------
    Area: A 1-D numpy array
        Area[i] is the area of the i-th triangle 
    
    Notes
    ------
    Using Eliezer's compute_face_measures() in lbopy.py to do so.  
     
    """
    import numpy as np
    Area = np.zeros(Meshes.shape[0])
    i = 0
    for Triangle in Meshes: # Shoot, I cannot use enumerate() for numpy array
        a = np.linalg.norm(Nodes[Triangle[0]] - Nodes[Triangle[1]])
        b = np.linalg.norm(Nodes[Triangle[1]] - Nodes[Triangle[2]])
        c = np.linalg.norm(Nodes[Triangle[2]] - Nodes[Triangle[0]])
        s = (a+b+c)/2.0

        Area[i] = np.sqrt(s*(s-a)*(s-b)*(s-c))
        i += 1
    return Area

def geometric_laplacian(Nodes, Faces):
    """The portal function to compute geometric laplacian
    
    Parameters
    ----------
    Nodes : 2-D numpy array 
        Nodes[i] is the 3-D coordinates of nodes on a mesh 
    Faces : 2-D numpy array
        Faces[i] is a 3-element array containing the indexes of nodes 

    Returns
    -------
    eigenvalues : a list of floats
        The Laplacian-Beltrami Spectrum 
    
    Notes
    ------
    
    This algorithm is described in Section 2.1.1 Discrete geometric Laplacians
    Steps:
    1. Compute W (can directly use Eliezer's cotangent kernel)
    2. Compute V = diag(v_1,...v_n) where v_i = \sum_{j\in N(i)} w_{ij} 
       and N(i) is the set of neighbors of node i.
    3. Compute stiffness matrix A = V - W 
    4. Compute the mass matrix D = diag(d_1, ..., d_n) where 
       d_i = a(i)/3 and a(i) is the area of all triangles at node i 
       (Here we adopt Eq. (4) of Reuter's paper)
    5. Solve the generalized eigenvalue problems Af = \lambda D f where \lambda 
       represents the reciprocal of eigenvalues we want.  
    
    """
    
    def masses(Nodes, Areas, Faces_at_Nodes):
        """Computer the mass matrix D = diag(d_1, ..., d_n) where 
           d_i = a(i)/3 and a(i) is the area of all triangles at node i 
           (Here we adopt Eq. (4) of Reuter's paper)    
    
        Parameters
        -----------
        
        Nodes : 2-D numpy array 
            Nodes[i] is the 3-D coordinates of nodes on a mesh 
        Meshes : 2-D numpy array
            Meshes[i] is a 3-element array containing the indexes of nodes 
        Area: A 1-D numpy array
            Area[i] is the area of the i-th triangle 
        Faces_at_Nodes: a 2-D list
            Faces_at_Nodes[i] is a list of IDs of faces at node i.
        d: a list of floats
            The sequence d_i, ..., d_n in Eq.(4)
        
        Returns
        ---------
        D: a sparse diagonal matrix
            The mass matrix
        
        """
    #    import numpy as np
        from scipy.sparse import lil_matrix
        
        num_nodes = Nodes.shape[0]

        d = [sum([Areas[j] for j in Faces_at_Nodes[i]]) for i in range(num_nodes)]
        D = lil_matrix((num_nodes, num_nodes))
        D.setdiag(d)
        
        D /= 3 
        return D

    import numpy

    num_nodes = len(Nodes)

    if num_nodes < 5: # too small
        print "The input size is too small. Skipped."
        return numpy.array([-1,-1,-1, -1, -1])
        
    import mindboggle.utils.kernels
    W = mindboggle.utils.kernels.cotangent_kernel(Nodes, Faces)
    W /= 2
    
    import mindboggle.utils.mesh
    Neighbor = mindboggle.utils.mesh.find_neighbors(Faces, num_nodes)
     
    V = gen_V(Faces, W, Neighbor)
    A = V - W # the stiffness matrix
    Area = area(Nodes, Faces)
    
    Faces_at_Nodes = mindboggle.utils.mesh.find_faces_at_vertices(Faces, num_nodes)
    D = masses(Nodes, Area, Faces_at_Nodes)  
    D = D.toarray()

#    L = numpy.dot(numpy.linalg.inv(D), A)
#    eigenvalues, eigenfunctions = numpy.linalg.eig(L)

    from scipy.sparse.linalg import eigsh, eigs 
    # note eigs is for nonsymmetric matrixes while eigsh is for  real-symmetric or complex-hermitian matrices
    
    eigenvalues, eigenvectors = eigs(A, k=3, M=D)
    eigenvalues = 1/eigenvalues
    
    return eigenvalues

def fem_laplacian(Nodes, Faces):
    """The portal function to compute geometric laplacian
    
    Parameters
    ----------
    Nodes : 2-D numpy array 
        Nodes[i] is the 3-D coordinates of nodes on a mesh 
    Faces : 2-D numpy array
        Faces[i] is a 3-element array containing the indexes of nodes 

    Returns
    -------
    eigenvalues : a list of floats
        The Laplacian-Beltrami Spectrum 
    
    Notes
    ------
    
    This is how Forrest got the steps from the paper:
    1. The FEM Laplacian problem is given as 
       A_{cot}\mathbf{f} = - \lambda B \mathbf{f} in the paper (the next equation after Eq. 6)
       We denote this equation in the docstring as Eq.A.
    2. Let L' = - B^{-1} A_{cot}
    3. Then Eq.A can be rewritten as 
        L' \mathbf{f} = \lambda \mathbf{f}
    4. Similarly to geometric Laplacian, the FEM Laplacian spectrum is then the 
       eigenvalues of L' .
 
    Steps:
    We could heavily reuse the code for geometric Laplacian.
    
    1. Compute W (can directly use Eliezer's cotangent kernel)
    2. Compute V = diag(v_1,...v_n) where v_i = \sum_{j\in N(i)} w_{ij} 
       and N(i) is the set of neighbors of node i.
    3. Compute stiffness matrix A = V - W. 
       Note that W and V are two cases for A_{cot}.
       A is -A_{cot}   (A_{cot} should be W - V)
    4. Compute the mass matrix B according to the paper.    
       B = P + Q where P[i,j] = (Area[x] + Area[y])/2 for x and y 
       are the two faces sharing the edge (i,j) (0's, otherwise), and
       Q[i,j] = (\sum_{k\in N(i)} Area[k] )/6 for i=j (0's, otherwise)
        
       I assume by the notation \sum_{k\in N(i)} |t_k| in the paper, 
       the authors mean total area of all triangles centered at node i.
       There is some ambiguity here because N(i) is the set of neighbor nodes 
       of node i (defined earlier in the paper) whereas t_k is a triangle.
       This is my best guess.  
        
    5. L = inv(B)*A
    """
    
    def gen_P(edges, faces_at_edges, Area, num_nodes):
        """Generate the P mentioned in pseudocode above
        """
       
        from scipy.sparse import lil_matrix
        P = lil_matrix((num_nodes, num_nodes))
#        P = numpy.zeros((num_nodes, num_nodes))
        for [i,j] in edges:
            P[i,j] = sum([Area[face] for face in faces_at_edges[(i,j)]]) # this line replaces the block commented below
            # =-------------------
#            facing_edges = faces_at_edges[(i,j)]
#            if len(facing_edges) == 1:  
#                [t1]= facing_edges
#                P[i,j] = Area[t1] 
#            else:
#                [t1,t2]= facing_edges
#                P[i,j] = Area[t1] + Area[t2]
            #=---------------------------------
    
        return P/12
        
    def gen_Q(edges, faces_at_edges, Area, num_nodes, Neighbor, Faces_at_Nodes):
        """Generate the Q mentioned in pseudocode above
        """
        from scipy.sparse import lil_matrix
        Q = lil_matrix((num_nodes, num_nodes))
        q = [sum([Area[k] for k in Faces_at_Nodes[i]]) for i in range(num_nodes)]
        Q.setdiag(q)        

        return Q/6
    
    import numpy
          
    num_nodes = len(Nodes)
    
    if num_nodes < 5: # too small
        print "The input size is too small. Skipped."
        return numpy.array([-1,-1,-1, -1, -1])
    
    import mindboggle.utils.kernels
    W = mindboggle.utils.kernels.cotangent_kernel(Nodes, Faces)
    W /= 2
    
    import mindboggle.utils.mesh
    Neighbor = mindboggle.utils.mesh.find_neighbors(Faces, num_nodes)
     
    V = gen_V(Faces, W, Neighbor)
    A = V - W # the stiffness matrix
    
    Area = area(Nodes, Faces)
    Faces_at_Nodes = mindboggle.utils.mesh.find_faces_at_vertices(Faces, num_nodes)
    # up to this point, the computation is the same as in geometric Laplacian
    
    faces_at_edges = mindboggle.utils.mesh.find_faces_at_edges(Faces)
    edges = mindboggle.utils.mesh.find_edges(Faces.tolist())
    
    P = gen_P(edges, faces_at_edges, Area, num_nodes)
    Q = gen_Q(edges, faces_at_edges, Area, num_nodes, Neighbor, Faces_at_Nodes)
    B = P + Q
    B = B.toarray()   

    A = A.toarray()
    
#    L = numpy.dot(numpy.linalg.inv(B),A)
#    eigenvalues, eigenfunctions = numpy.linalg.eig(L)

    from scipy.sparse.linalg import eigsh, eigs 
    # note eigs is for nonsymmetric matrixes while eigsh is for  real-symmetric or complex-hermitian matrices
    
    eigenvalues, eigenvectors = eigs(A, k=3, M=B)
    eigenvalues = 1/eigenvalues
    
    return eigenvalues

if __name__ == "__main__":
    import numpy as np
    # You should get different output if you only change the coordinates of nodes.
    # If you do NOT see the changes, you are computing graph laplacian.
    

    # Use some vertices on a cube. First, define a cube.  
    nodes = [[0,0,0], [1,0,0], [0,0,1], [0,1,1], [1,0,1], [0,1,0], [1,1,1], [1,1,0]]
    nodes = np.array(nodes)
    # Then, pick some faces. 
    faces = [[0,2,4], [0,1,4], [2,3,4], [3,4,5], [3,5,6], [0,1,7]] # note, all points must be on faces. O/w, you get singular matrix error when inverting D
    faces = np.array(faces)
    geometric_LBS = geometric_laplacian(nodes, faces)
    fem_LBS = fem_laplacian(nodes, faces)
    
    print "the geometric LBS is:", list(geometric_LBS)
    print "the FEM LBS is:", list(fem_LBS)
    