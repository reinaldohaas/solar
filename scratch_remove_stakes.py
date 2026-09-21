with open(r"C:\Users\haas\github\solar\gerar_visualizador_campo_salao.py", "r", encoding="utf-8") as f:
    code = f.read()

# Substituir o bloco das tesouras por um conjunto estrutural limpo que fica 100% por baixo da telha
old_truss_block = """    // 3 TESOURAS TRADICIONAIS COM PENDURAL CENTRAL NO ALINHAMENTO DA CUMEEIRA (Z = 0)
    [-5.7, 0, 5.7].forEach(x => {
      const truss = new THREE.Group();
      truss.position.set(x, 0, 0);

      const tieBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 8.2, 10), rusticWoodMat);
      tieBeam.rotation.x = Math.PI / 2;
      tieBeam.position.set(0, 3.65, 0);
      truss.add(tieBeam);

      // Pendural Central Vertical (Exatamente no centro Z = 0)
      const kingPost = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 1.65, 10), rusticWoodMat);
      kingPost.position.set(0, 4.45, 0);
      truss.add(kingPost);

      // Pernas da tesoura
      const rafterLen = 4.35;
      const angleRafter = Math.atan2(1.60, 4.0);
      
      const rafterN = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, rafterLen, 10), rusticWoodMat);
      rafterN.rotation.x = -angleRafter; rafterN.position.set(0, 4.45, -2.0);
      truss.add(rafterN);

      const rafterS = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, rafterLen, 10), rusticWoodMat);
      rafterS.rotation.x = angleRafter; rafterS.position.set(0, 4.45, 2.0);
      truss.add(rafterS);

      const strutN = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 1.8, 8), rusticWoodMat);
      strutN.rotation.x = Math.PI / 4; strutN.position.set(0, 4.2, -1.2);
      const strutS = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 1.8, 8), rusticWoodMat);
      strutS.rotation.x = -Math.PI / 4; strutS.position.set(0, 4.2, 1.2);
      truss.add(strutN, strutS);

      optGroup1.add(truss);
    });"""

new_truss_block = """    // 3 TESOURAS TRADICIONAIS LIMPAS (100% EMBUTIDAS SOB O TELHADO, SEM NENHUMA ESTACA SAINDO)
    [-5.7, 0, 5.7].forEach(x => {
      const truss = new THREE.Group();
      truss.position.set(x, 0, 0);

      // Tirante Horizontal (Linha da Tesoura)
      const tieBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 8.0, 10), rusticWoodMat);
      tieBeam.rotation.x = Math.PI / 2;
      tieBeam.position.set(0, 3.60, 0);
      truss.add(tieBeam);

      // Pendural Central Vertical (termina a 4.90m, embutido sob a cumeeira que fica em 5.25m)
      const kingPost = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, 1.25, 10), rusticWoodMat);
      kingPost.position.set(0, 4.25, 0); // Vai de y=3.62m até y=4.88m, 100% por baixo da telha
      truss.add(kingPost);

      optGroup1.add(truss);
    });"""

code = code.replace(old_truss_block, new_truss_block)

# Ajustar viga de cumeeira para ficar por baixo das telhas
code = code.replace(
    "ridgeBeam.position.set(0, 5.25, 0);",
    "ridgeBeam.position.set(0, 5.15, 0);"
)

# Na Opção 2 (Metálica): garantir que o pontalete não fure o telhado
old_opt2_truss = """      const post = new THREE.Mesh(new THREE.BoxGeometry(0.10, 1.5, 0.10), steelDarkMat);
      post.position.set(0, 4.35, 0); mTruss.add(post);"""

new_opt2_truss = """      const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.10, 0.08), steelDarkMat);
      post.position.set(0, 4.15, 0); mTruss.add(post);"""

code = code.replace(old_opt2_truss, new_opt2_truss)

with open(r"C:\Users\haas\github\solar\gerar_visualizador_campo_salao.py", "w", encoding="utf-8") as f:
    f.write(code)

print("gerar_visualizador_campo_salao.py corrigido: estacas removidas!")
