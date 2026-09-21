#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o projeto executivo nativo do QGIS (.qgs) para o Sítio das Andorinhas,
com as novas camadas de Drone e MDT Estendido organizadas em SIRGAS 2000 UTM 22S (EPSG:31982).
"""

import os

SOLAR_DIR = r"C:\Users\haas\github\solar"
QGS_OUT = os.path.join(SOLAR_DIR, "Projeto_Solar_Sitio_das_Andorinhas.qgs")

qgs_xml = """<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="Projeto Solar - Sítio das Andorinhas & Drone (Nativo SIGSC)" version="3.28.0">
  <homePath path=""/>
  <title>Projeto Solar e Relevo 3D - Sítio das Andorinhas & Drone</title>
  <autotransaction active="0"/>
  <evaluateDefaultValues active="0"/>
  <trust active="0"/>
  <projectCrs>
    <spatialrefsys nativeFormat="Wkt">
      <wkt>PROJCRS["SIRGAS 2000 / UTM zone 22S",BASEGEOGCRS["SIRGAS 2000",DATUM["Sistema de Referencia Geocentrico para las Americas 2000",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4674]],CONVERSION["UTM zone 22S",METHOD["Transverse Mercator",ID["EPSG",9807]],PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8801]],PARAMETER["Longitude of natural origin",-51,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8802]],PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1],ID["EPSG",8805]],PARAMETER["False easting",500000,LENGTHUNIT["metre",1],ID["EPSG",8806]],PARAMETER["False northing",10000000,LENGTHUNIT["metre",1],ID["EPSG",8807]]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT["metre",1]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["metre",1]],USAGE[SCOPE["Engineering survey, topographic mapping."],AREA["Brazil - between 54°W and 48°W, northern and southern hemispheres, onshore and offshore."],BBOX[-33.77,-54,5.27,-48]],ID["EPSG",31982]]</wkt>
      <proj4>+proj=utm +zone=22 +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs</proj4>
      <srsid>27208</srsid>
      <srid>31982</srid>
      <authid>EPSG:31982</authid>
      <description>SIRGAS 2000 / UTM zone 22S</description>
      <projectionacronym>utm</projectionacronym>
      <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
      <geographicflag>false</geographicflag>
    </spatialrefsys>
  </projectCrs>
  <layer-tree-group>
    <customproperties>
      <Option/>
    </customproperties>
    <layer-tree-layer id="mesas_p1" name="UFV Solo P1 - 114 Mesas (925,68 kWp)" source="./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p1" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="mesas_p2" name="UFV Solo P2 - 73 Mesas (592,76 kWp)" source="./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p2" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="mesas_p3" name="UFV Solo P3 - 46 Mesas (373,52 kWp)" source="./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p3" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="salao" name="Salão Telhado Reto (Solar 10,44 kWp)" source="./Projeto_Solar_SIGSC_Nativo.gpkg|layername=edificacao_salao" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="campo" name="Campo de Areia e Redes 3D (22x12m)" source="./Projeto_Solar_SIGSC_Nativo.gpkg|layername=campo_de_areia" provider="ogr" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="orto_drone_nativa" name="Ortofoto Pura do Drone (Local 7,4 cm)" source="./Ortofoto_Drone_Local.tif" provider="gdal" expanded="1" checked="Qt::Checked"/>
    <layer-tree-layer id="orto_sigsc_estendida" name="Ortofoto Oficial SIGSC 0,39m (Referência Estadual)" source="./Ortofoto_SIGSC_Area_Estendida.tif" provider="gdal" expanded="0" checked="Qt::Unchecked"/>
    <layer-tree-layer id="mdt_drone_exata" name="MDT 1,0m SIGSC (Área Exata do Drone)" source="./MDT_SIGSC_Area_Drone_Exata.tif" provider="gdal" expanded="0" checked="Qt::Unchecked"/>
  </layer-tree-group>
  <projectlayers>
    <maplayer type="raster" id="orto_drone_nativa" name="Ortofoto Pura do Drone (Local 7,4 cm)" autoRefreshTime="0" autoRefreshMode="Disabled" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories">
      <extent>
        <xmin>662966.8328173596</xmin>
        <ymin>6967989.400200627</ymin>
        <xmax>664048.0222025294</xmax>
        <ymax>6969263.598495271</ymax>
      </extent>
      <id>orto_drone_nativa</id>
      <datasource>./Ortofoto_Drone_Local.tif</datasource>
      <provider>gdal</provider>
      <pipe>
        <provider><mode>1</mode></provider>
        <rasterrenderer type="multibandcolor" redBand="1" greenBand="2" blueBand="3" opacity="1" mode="0"/>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <rasterresampler maxOversampling="2"/>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>
    <maplayer type="raster" id="orto_drone_comp" name="Ortofoto Drone 2026/2024 & SIGSC (Estendida)" autoRefreshTime="0" autoRefreshMode="Disabled" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories">
      <extent>
        <xmin>662900</xmin>
        <ymin>6967950</ymin>
        <xmax>664150</xmax>
        <ymax>6969300</ymax>
      </extent>
      <id>orto_drone_comp</id>
      <datasource>./Ortofoto_Drone_Composicao_Estendida.tif</datasource>
      <provider>gdal</provider>
      <pipe>
        <provider><mode>1</mode></provider>
        <rasterrenderer type="multibandcolor" redBand="1" greenBand="2" blueBand="3" opacity="1" mode="0"/>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <rasterresampler maxOversampling="2"/>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>
    <maplayer type="raster" id="orto_drone_pura" name="Ortofoto Drone Pura (Transparente)" autoRefreshTime="0" autoRefreshMode="Disabled" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories">
      <extent>
        <xmin>662900</xmin>
        <ymin>6967950</ymin>
        <xmax>664150</xmax>
        <ymax>6969300</ymax>
      </extent>
      <id>orto_drone_pura</id>
      <datasource>./Ortofoto_Drone_Pura_Estendida.tif</datasource>
      <provider>gdal</provider>
      <pipe>
        <provider><mode>1</mode></provider>
        <rasterrenderer type="multibandcolor" redBand="1" greenBand="2" blueBand="3" opacity="1" mode="0"/>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <rasterresampler maxOversampling="2"/>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>
    <maplayer type="raster" id="orto_sigsc" name="Ortofoto Oficial SIGSC 0,39m (Sítio)" autoRefreshTime="0" autoRefreshMode="Disabled" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories">
      <extent>
        <xmin>663097.1710681518</xmin>
        <ymin>6968456.962679351</ymin>
        <xmax>664156.8010681518</xmax>
        <ymax>6968843.842679351</ymax>
      </extent>
      <id>orto_sigsc</id>
      <datasource>./Ortofoto_SIGSC_Novo_sitio_das_andorinhas.tif</datasource>
      <provider>gdal</provider>
      <pipe>
        <provider><mode>1</mode></provider>
        <rasterrenderer type="multibandcolor" redBand="1" greenBand="2" blueBand="3" opacity="1" mode="0"/>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <rasterresampler maxOversampling="2"/>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>
    <maplayer type="raster" id="mdt_estendido" name="MDT 1,0m SIGSC Estendido (Área do Drone - 168 ha)" autoRefreshTime="0" autoRefreshMode="Disabled" refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" hasScaleBasedVisibilityFlag="0" maxScale="0" minScale="1e+08" styleCategories="AllStyleCategories">
      <extent>
        <xmin>662900</xmin>
        <ymin>6967950</ymin>
        <xmax>664150</xmax>
        <ymax>6969300</ymax>
      </extent>
      <id>mdt_estendido</id>
      <datasource>./MDT_SIGSC_Area_Drone_Estendida.tif</datasource>
      <provider>gdal</provider>
      <pipe>
        <provider><mode>1</mode></provider>
        <rasterrenderer type="singlebandpseudocolor" band="1" opacity="1" classificationMin="378" classificationMax="740">
          <rastershader>
            <colorrampshader colorRampType="INTERPOLATED" clip="0" classificationMode="1">
              <colorramp type="gradient" name="[source]">
                <Option type="Map">
                  <Option type="QString" name="color1" value="43,131,186,255"/>
                  <Option type="QString" name="color2" value="215,25,28,255"/>
                  <Option type="QString" name="stops" value="0.25;171,221,164,255:0.5;255,255,191,255:0.75;253,174,97,255"/>
                </Option>
              </colorramp>
              <item label="378 m" color="#2b83ba" value="378"/>
              <item label="470 m" color="#abdda4" value="470"/>
              <item label="560 m" color="#ffffbf" value="560"/>
              <item label="650 m" color="#fdae61" value="650"/>
              <item label="740 m" color="#d7191c" value="740"/>
            </colorrampshader>
          </rastershader>
        </rasterrenderer>
        <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
        <rasterresampler maxOversampling="2"/>
      </pipe>
      <blendMode>0</blendMode>
    </maplayer>
    <maplayer type="vector" id="mesas_p1" name="UFV Solo P1 - 114 Mesas (925,68 kWp)" geometry="Polygon" readOnly="0">
      <id>mesas_p1</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p1</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="25,100,200,220"/>
                <Option type="QString" name="outline_color" value="255,255,255,255"/>
                <Option type="QString" name="outline_width" value="0.3"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
    <maplayer type="vector" id="mesas_p2" name="UFV Solo P2 - 73 Mesas (592,76 kWp)" geometry="Polygon" readOnly="0">
      <id>mesas_p2</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p2</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="35,130,220,220"/>
                <Option type="QString" name="outline_color" value="255,255,255,255"/>
                <Option type="QString" name="outline_width" value="0.3"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
    <maplayer type="vector" id="mesas_p3" name="UFV Solo P3 - 46 Mesas (373,52 kWp)" geometry="Polygon" readOnly="0">
      <id>mesas_p3</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=mesas_ufv_p3</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="50,150,240,220"/>
                <Option type="QString" name="outline_color" value="255,255,255,255"/>
                <Option type="QString" name="outline_width" value="0.3"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
    <maplayer type="vector" id="salao" name="Salão Telhado Reto (Solar 10,44 kWp)" geometry="Polygon" readOnly="0">
      <id>salao</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=edificacao_salao</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="230,120,40,220"/>
                <Option type="QString" name="outline_color" value="40,40,40,255"/>
                <Option type="QString" name="outline_width" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
    <maplayer type="vector" id="campo" name="Campo de Areia e Redes 3D (22x12m)" geometry="Polygon" readOnly="0">
      <id>campo</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=campo_de_areia</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="240,210,140,220"/>
                <Option type="QString" name="outline_color" value="120,90,30,255"/>
                <Option type="QString" name="outline_width" value="0.8"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
    <maplayer type="vector" id="limite" name="Limite Sítio das Andorinhas (18,60 ha)" geometry="Polygon" readOnly="0">
      <id>limite</id>
      <datasource>./Projeto_Solar_SIGSC_Nativo.gpkg|layername=limite_sitio</datasource>
      <provider encoding="UTF-8">ogr</provider>
      <renderer-v2 type="singleSymbol" symbollevels="0">
        <symbols>
          <symbol type="fill" name="0" alpha="1" clip_to_extent="1">
            <layer pass="0" class="SimpleFill" locked="0">
              <Option type="Map">
                <Option type="QString" name="color" value="0,0,0,0"/>
                <Option type="QString" name="outline_color" value="255,234,0,255"/>
                <Option type="QString" name="outline_width" value="1.2"/>
              </Option>
            </layer>
          </symbol>
        </symbols>
      </renderer-v2>
    </maplayer>
  </projectlayers>
</qgis>"""

def main():
    with open(QGS_OUT, 'w', encoding='utf-8') as f:
        f.write(qgs_xml)
    print(f"Projeto QGIS Atualizado com Sucesso: {QGS_OUT}")

if __name__ == '__main__':
    main()
