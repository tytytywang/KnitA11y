from typing import Optional, Dict, List, Union, Tuple
import networkx as nx
from knit_graphs.Knit_Graph import Knit_Graph
from knit_graphs.Yarn import Yarn #just for the draw_rebulit_graph(), which we afterwards will move to New_Hole_Generator Module
import matplotlib.pyplot as plt

from pyvis import network as nw

from bokeh.models import (BoxZoomTool, Circle, HoverTool, LabelSet, Arrow, NormalHead, OpenHead, VeeHead, Label,
                          MultiLine, Plot, Range1d, ResetTool, TapTool, BoxSelectTool, WheelZoomTool)
from bokeh.palettes import Category20_20
from bokeh.plotting import figure, from_networkx, show
from bokeh.resources import CDN
from bokeh.embed import file_html
import holoviews as hv
from holoviews import opts
import numpy as np
from bokeh.plotting import show

class knitGraph_visualizer:
    """
    :param knit_graph: the knit graph to visualize
    :param yarn_start_direction: the starting direction of the yarn, value include 'left to right' or 'right to left'.
    """
    def __init__(self, knit_graph: Knit_Graph):
        self.knit_graph: Knit_Graph = knit_graph
        self.object_type = knit_graph.object_type
        # self.yarn_start_direction = yarn_start_direction
        self.yarn_start_direction =  knit_graph.yarn_start_direction
        print(f'self.yarn_start_direction in viz is {self.yarn_start_direction}, knit_graph.yarn_start_direction in viz is {knit_graph.yarn_start_direction}')
        self.node_to_course_and_wale: Dict[int, (int, int)] = knit_graph.node_to_course_and_wale
        self.node_on_front_or_back: Dict[int, str] = knit_graph.node_on_front_or_back
        print('node_to_course_and_wale viz', self.node_to_course_and_wale)
        print('node_on_front_or_back viz', self.node_on_front_or_back)
        # print('course_and_wale_and_bed_to_node viz', self.course_and_wale_and_bed_to_node)
        self.nodes_to_positions: Dict[int, Dict[str, float]] = {}
        # we assume different carrier carry yarns of differnt color, though practically they can be the same.
        self.carrier_id_to_color = {1:'black', 2:'skyblue', 3:'orange', 4:'green', 5: 'yellow', 6:'blue', 7: 'pink', 8: 'purple', 9:'cyan', 10:'red'}
        self.cable_depth_to_color = {1:'grey', -1:'magenta'}
        self.alpha_front = 1
        self.alpha_back = 0.5 #previously 0.7
        self.node_color_property = {}
        self.edge_color_property = {}
        self.stitch_labels = {}
        self.yarns = [*knit_graph.yarns.values()]
        #distance related param for tube
        self.h_back2front, self.w_back2front, self.w_between_node, self.h_course = 0.15, 0.1, 1, 1
    #below are skeletal functions to complete visualization
    #set node postion
    def get_nodes_position(self): 
        x0 = 0
        y0 = 0
        for node in self.knit_graph.graph.nodes:
            self.nodes_to_positions[node] = {}
            self.node_color_property[node] = {}
            course = self.node_to_course_and_wale[node][0]
            wale = self.node_to_course_and_wale[node][1]
            if self.node_on_front_or_back[node] == 'f':
                x0 = 0 #initialize x0 from 0.3 to 0
                if self.yarn_start_direction == 'left to right':
                    self.nodes_to_positions[node]['x'] = x0 + wale * self.w_between_node
                elif self.yarn_start_direction == 'right to left':
                    self.nodes_to_positions[node]['x'] = x0 - wale * self.w_between_node
                self.nodes_to_positions[node]['y'] = y0 + course * self.h_course
            elif self.node_on_front_or_back[node] == 'b':
                # if self.object_type == 'pocket' or self.object_type == 'handle':
                if self.object_type == 'tube':
                    x0 = 0  #0.6
                    h_course =  1*self.h_course
                    if self.yarn_start_direction == 'left to right':
                        self.nodes_to_positions[node]['x'] = x0 + wale * self.w_between_node
                    elif self.yarn_start_direction == 'right to left':
                        self.nodes_to_positions[node]['x'] = x0 - wale * self.w_between_node
                    # self.nodes_to_positions[node]['y'] = y0 + course * h_course
                    self.nodes_to_positions[node]['y'] = y0 + course * self.h_course + self.h_back2front
                else:
                    if self.yarn_start_direction == 'left to right':
                        self.nodes_to_positions[node]['x'] = x0 + wale * self.w_between_node + self.w_back2front
                    elif self.yarn_start_direction == 'right to left':
                        self.nodes_to_positions[node]['x'] = x0 - wale * self.w_between_node + self.w_back2front
                    self.nodes_to_positions[node]['y'] = y0 + course * self.h_course + self.h_back2front
        # print(f'nodes_to_positions is {self.nodes_to_positions}')
    #set node color
    def get_nodes_color(self):
        print(f'in knit viz, nodes is {self.knit_graph.graph.nodes}')
        for node in self.knit_graph.graph.nodes:
            #find carrier_id of the node
            #first identify the yarn of the node
            for yarn in self.yarns:
                if node in yarn:
                    carrier_id = yarn.carrier.carrier_ids
                    break
            print(f'in knit viz, node is {node}, carrier_id is {carrier_id}')
            #store node color property
            self.node_color_property[node]['color'] = self.carrier_id_to_color[carrier_id]
            self.node_color_property[node]['alpha'] = self.alpha_front if self.node_on_front_or_back[node] == 'f' else self.alpha_back
    #get yarn edges color
    def get_yarn_edges(self):
        #add yarn edges and set edge color
        print(f'len(self.yarns) is {len(self.yarns)}')
        for yarn in self.yarns:
            print(f'yarn is {yarn.yarn_id}, yarn.yarn_graph.edges is {yarn.yarn_graph.edges}')
            for prior_node, next_node in yarn.yarn_graph.edges:
                if prior_node == next_node:
                    continue #(n, n) are mistakenly added to yarn_graph edges, will need to identify the issue source later, here we just use a trick.
                if prior_node not in self.nodes_to_positions or next_node not in self.nodes_to_positions:
                    continue
                self.edge_color_property[(prior_node, next_node)] = {}
                carrier_id = yarn.carrier.carrier_ids
                self.edge_color_property[(prior_node, next_node)]['color'] = self.carrier_id_to_color[carrier_id]
                #As long as either node on the edge is on the front, then the edge is regarded as on the front and will be colored brighter
                self.edge_color_property[(prior_node, next_node)]['alpha'] = self.alpha_front if self.node_on_front_or_back[prior_node] == 'f' and self.node_on_front_or_back[next_node] == 'f' else self.alpha_back
        print(f'self.edge_color_property is {self.edge_color_property}')
    #get stitch edges color
    def get_stitch_edges(self):
        #add stitch edges and set edge color
        for parent_id, child_id in self.knit_graph.graph.edges:
            self.edge_color_property[(parent_id, child_id)] = {}
            self.edge_color_property[(parent_id, child_id)]['alpha'] = self.alpha_front if self.node_on_front_or_back[parent_id] == 'f' and self.node_on_front_or_back[child_id] == 'f' else self.alpha_back
            # self.stitch_labels[(parent_id, child_id)] = self.knit_graph.graph[parent_id][child_id]["pull_direction"].opposite() if self.node_on_front_or_back[child_id] == 'b' else self.knit_graph.graph[parent_id][child_id]["pull_direction"]
            #unlike above (the original), we do not invert the stitch pull direction on the back bed
            self.stitch_labels[(parent_id, child_id)] = self.knit_graph.graph[parent_id][child_id]["pull_direction"]
            flag_for_on_yarn = False
            for yarn in self.yarns:
                #if stitch edge color is determined by child_id, use below one
                # if child_id in yarn:
                #if stitch edge color is determined by parent_id, use below one
                if parent_id in yarn:
                    flag_for_on_yarn = True
                    carrier_id = yarn.carrier.carrier_ids
                    self.edge_color_property[(parent_id, child_id)]['color'] = self.carrier_id_to_color[carrier_id]
                    break
            if self.knit_graph.graph[parent_id][child_id]["depth"] < 0:
                depth = -1
                self.edge_color_property[(parent_id, child_id)]['color'] = self.cable_depth_to_color[depth]
            elif self.knit_graph.graph[parent_id][child_id]["depth"] > 0:
                depth = 1
                self.edge_color_property[(parent_id, child_id)]['color'] = self.cable_depth_to_color[depth]
                        #if nodes not on any yarns, then it will be colored 'maroon'
            if flag_for_on_yarn == False:
                self.edge_color_property[(parent_id, child_id)]['color'] = 'maroon'
        print(f'self.stitch_labels is {self.stitch_labels}')
    # draw the graph
    def draw_graph(self):
        #create a graph
        G = nx.DiGraph()
        #derive position of nodes
        pos ={}
        for node in self.nodes_to_positions:
            pos[node] = [*self.nodes_to_positions[node].values()]
        #add nodes
        G.add_nodes_from(pos.keys())
        #draw nodes
        for node in G.nodes():
            # node_size = 500 
            #bigger node size: 1000
            nx.draw_networkx_nodes(G, pos, nodelist=[node], node_size = 500, node_color = self.node_color_property[node]['color'], alpha = self.node_color_property[node]['alpha'])
        #draw edges
        # for edge in [*self.edge_color_property.keys()]:
        #     # width = 3.0
        #     # bigger version: width = 10
        #     nx.draw_networkx_edges(G, pos, edgelist=[edge], width = 5.0, edge_color = self.edge_color_property[edge]['color'], style = 'solid', alpha = self.edge_color_property[edge]['alpha'])
        #draw edges using different line styles
        for edge in [*self.edge_color_property.keys()]: 
            #width = 5.0
            if edge in self.stitch_labels and str(self.stitch_labels[edge]) == 'FtB':
                nx.draw_networkx_edges(G, pos, edgelist=[edge], width = 8.0, edge_color = self.edge_color_property[edge]['color'], node_size = 200, arrowstyle = '-', arrowsize= 20, style = 'dashed', alpha = self.edge_color_property[edge]['alpha'])
            elif edge in self.stitch_labels and str(self.stitch_labels[edge]) == 'BtF':
                nx.draw_networkx_edges(G, pos, edgelist=[edge], width = 8.0, edge_color = self.edge_color_property[edge]['color'],  node_size = 200, arrowstyle = '-', style = 'solid', alpha = self.edge_color_property[edge]['alpha'])
            else:
                nx.draw_networkx_edges(G, pos, edgelist=[edge], width = 8.0, edge_color = self.edge_color_property[edge]['color'], node_size = 300, arrows = True, style = 'solid', alpha = self.edge_color_property[edge]['alpha'])
        #draw node labels: font_size = 9 bigger font: 20
        # node_labels = {x: x for x in G.nodes}
        # nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=9, font_color='w') 
        #draw edge labels
        # label_pos = 0.5, font_size = 5
        # small version: label_pos = 0.5, font_size = 0.0005
        # nx.draw_networkx_edge_labels(G, pos, edge_labels = self.stitch_labels, label_pos = 0.5, font_size = 0.05, font_color='k', rotate=False)
        plt.show()

    def deprecated_draw_graph_holoviews(self):
        #create a graph
        G = nx.DiGraph()
        #derive position of nodes
        pos = {}
        for node in self.nodes_to_positions:
            pos[node] = [*self.nodes_to_positions[node].values()]
            #print(node, pos[node])
        #add nodes
        G.add_nodes_from(pos.keys())
        #G.add_edges_from([*self.edge_color_property.keys()])
        hv.extension('bokeh')
        simple_graph = hv.Graph.from_networkx(G, pos).opts(width=1350, height=1000, inspection_policy='nodes')
        # print("begin")
        # print(list(G.nodes))
        # print("done")
        # directed_graph = simple_graph.opts(inspection_policy='nodes', arrowhead_length=0.015, directed=True, width=1000, height=1000, aspect='equal')

        # #create a graph
        # G = nx.DiGraph()
        # #derive position of nodes
        # pos ={}
        # for node in self.nodes_to_positions:
        #     pos[node] = [*self.nodes_to_positions[node].values()]
        #     #print(node, pos[node])
        # #add nodes
        # G.add_nodes_from(pos.keys())
        # graph = from_networkx(G,  pos, scale=7, center=(-10,10))
        # p = figure(x_range=(-10, 5), y_range=(-5, 10),
        #    x_axis_location=None, y_axis_location=None,
        #    tools="hover", tooltips="wale: @wale")

        # #graph.node_renderer.data_source.data['colors'] = 'red'
        # graph.node_renderer.glyph.update(size=10)
        # p.renderers.append(graph)
        p = hv.render(simple_graph)

        x_range = np.abs(p.x_range.start - p.x_range.end)
        y_range = np.abs(p.y_range.start - p.y_range.end)

        hover = HoverTool(tooltips=[("Course:", "@course"), ("Wale:", "@wale")])
        p.add_tools(hover, TapTool(), BoxSelectTool(), WheelZoomTool())


        for edge in [*self.edge_color_property.keys()]:
            vec_start = np.array([pos[edge[0]][0], pos[edge[0]][1]])
            vec_end = np.array([pos[edge[1]][0], pos[edge[1]][1]])
            vec_dir = (vec_start - vec_end) / np.linalg.norm(vec_start - vec_end)
            radius_x = 0.008 * x_range
            radius_y = 0.01 * y_range
            p.add_layout(Arrow(end=NormalHead(fill_color=self.edge_color_property[edge]['color'], fill_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha']), size=7),
                x_start=(pos[edge[0]][0] - radius_x * vec_dir[0]), y_start=(pos[edge[0]][1] - radius_y * vec_dir[1]), x_end=(pos[edge[1]][0] + radius_x * vec_dir[0]), y_end=(pos[edge[1]][1] + radius_y * vec_dir[1]), line_width=3, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
            edge_x = (pos[edge[0]][0] + pos[edge[1]][0]) / 2
            edge_y = (pos[edge[0]][1] + pos[edge[1]][1]) / 2
            if edge in self.stitch_labels:
                label = Label(x=edge_x, y=edge_y, text=str(self.stitch_labels[edge]), x_offset=-8, y_offset=-6, text_color="black", text_alpha=1, text_font_size='9px', text_font_style='bold')
                p.add_layout(label)

        for node in G.nodes:
            label = Label(x=pos[node][0], y=pos[node][1], text=str(node), x_offset=(-3 * len(str(node))), y_offset=-3.5, text_color="white", text_font_size='10px', text_font_style='bold')
            p.add_layout(label)

        graph = p.renderers[-1]

        graph.node_renderer.data_source.data['colors'] = [self.node_color_property[node]['color'] for node in G.nodes()]
        graph.node_renderer.data_source.data['alpha'] = [self.node_color_property[node]['alpha'] * self.node_color_property[node]['alpha'] for node in G.nodes()]
        graph.node_renderer.data_source.data['course'] = [self.node_to_course_and_wale[node][0] for node in self.node_to_course_and_wale]
        graph.node_renderer.data_source.data['wale'] = [self.node_to_course_and_wale[node][1] for node in self.node_to_course_and_wale]


        graph.edge_renderer.data_source.data['alpha'] = [0 for edge in G.edges()]
        graph.node_renderer.glyph.update(size=20, fill_color="colors", fill_alpha="alpha")
        graph.edge_renderer.glyph.update(line_alpha="alpha")

        html = file_html(p, CDN, "knit graph visualization")
        return html

    def draw_graph_holoviews(self):
        # create a graph
        G = nx.DiGraph()
        # derive position of nodes
        pos = {}
        for node in self.nodes_to_positions:
            pos[node] = [*self.nodes_to_positions[node].values()]

        # add nodes
        G.add_nodes_from(pos.keys())
        hv.extension('bokeh')
        simple_graph = hv.Graph.from_networkx(G, pos).opts(width=950, height=1000, inspection_policy='nodes', node_hover_fill_color='red')
        p = hv.render(simple_graph)

        x_range = np.abs(p.x_range.start - p.x_range.end)
        y_range = np.abs(p.y_range.start - p.y_range.end)

        # hover = HoverTool(tooltips=[("Course:", "@course"), ("Wale:", "@wale")])
        hover = HoverTool(tooltips=[("Course:", "@course"), ("Wale:", "@wale"), ("Bed:", "@bed")])
        p.add_tools(hover, TapTool(), BoxSelectTool()) #p.add_tools(hover, TapTool(), BoxSelectTool(), WheelZoomTool())

        for edge in [*self.edge_color_property.keys()]:
            # vec_start = np.array([pos[edge[0]][0], pos[edge[0]][1]])
            # vec_end = np.array([pos[edge[1]][0], pos[edge[1]][1]])
            # vec_dir = (vec_start - vec_end) / np.linalg.norm(vec_start - vec_end)
            # radius_x = 0.008 * x_range
            # radius_y = 0.01 * y_range

            # p.add_layout(Arrow(end=NormalHead(fill_color=self.edge_color_property[edge]['color'], fill_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha']), size=7),
            #     x_start=(pos[edge[0]][0] - radius_x * vec_dir[0]), y_start=(pos[edge[0]][1] - radius_y * vec_dir[1]), x_end=(pos[edge[1]][0] + radius_x * vec_dir[0]), \
            #         y_end=(pos[edge[1]][1] + radius_y * vec_dir[1]), line_width=3, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
            ######
            #add edges with arrow head
            # p.add_layout(Arrow(end=NormalHead(fill_color=self.edge_color_property[edge]['color'], fill_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha']), size=7), #size=7
            #     x_start=(pos[edge[0]][0]), y_start=(pos[edge[0]][1]), x_end=(pos[edge[1]][0]), \
            #         y_end=(pos[edge[1]][1]), line_width=3, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
            #######
            #add edges without arrow head, use Arrow(end=None, ...)
            if edge in self.stitch_labels and str(self.stitch_labels[edge]) == 'FtB':
                p.add_layout(Arrow(end=None, #size=7, line_width=3
                    x_start=(pos[edge[0]][0]), y_start=(pos[edge[0]][1]), x_end=(pos[edge[1]][0]), \
                        y_end=(pos[edge[1]][1]), line_width=1, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha']), line_dash='dashed'))
            elif edge in self.stitch_labels and str(self.stitch_labels[edge]) == 'BtF':
                p.add_layout(Arrow(end=None, #size=7, line_width=3
                    x_start=(pos[edge[0]][0]), y_start=(pos[edge[0]][1]), x_end=(pos[edge[1]][0]), \
                        y_end=(pos[edge[1]][1]), line_width=1, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
            else:
                #for yarn edges #size=7, line_width=3
                # print(f'edge is {edge}')
                #---
                p.add_layout(Arrow(end=NormalHead(fill_color=self.edge_color_property[edge]['color'], fill_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha']), size=2), #size=7
                x_start=(pos[edge[0]][0]), y_start=(pos[edge[0]][1]), x_end=(pos[edge[1]][0]), \
                    y_end=(pos[edge[1]][1]), line_width=1, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
                #---
                # p.add_layout(Arrow(end=None, #size=7
                # x_start=(pos[edge[0]][0]), y_start=(pos[edge[0]][1]), x_end=(pos[edge[1]][0]), \
                #     y_end=(pos[edge[1]][1]), line_width=1, line_color=self.edge_color_property[edge]['color'], line_alpha=(self.edge_color_property[edge]['alpha']*self.edge_color_property[edge]['alpha'])))
            
            edge_x = (pos[edge[0]][0] + pos[edge[1]][0]) / 2
            edge_y = (pos[edge[0]][1] + pos[edge[1]][1]) / 2
            #add stitch label
            # if edge in self.stitch_labels:
            #     label = Label(x=edge_x, y=edge_y, text=str(self.stitch_labels[edge]), x_offset=-8, y_offset=-6, text_color="black", text_alpha=1, text_font_size='8px', text_font_style='bold') #text_font_size='9px'
            #     p.add_layout(label)
        
        # add node id label 
        # for node in G.nodes:
        #     # label = Label(x=pos[node][0], y=pos[node][1], text=str(node), x_offset=(-3 * len(str(node))), y_offset=-3.5, text_color="white", text_font_size='4px', text_font_style='bold') #text_font_size='10px'
        #     label = Label(x=pos[node][0], y=pos[node][1], text=str(node), x_offset=(-1.2 * len(str(node))), y_offset=-1.5, text_color="white", text_font_size='6px', text_font_style='bold') #text_font_size='10px'
        #     p.add_layout(label)

        graph = p.renderers[-1]
        graph.node_renderer.data_source.data['colors'] = [self.node_color_property[node]['color'] for node in G.nodes()]
        #original for node alpha
        graph.node_renderer.data_source.data['alpha'] = [self.node_color_property[node]['alpha'] * self.node_color_property[node]['alpha'] for node in G.nodes()]
        #now for node alpha
        # graph.node_renderer.data_source.data['alpha'] = [0 for node in G.nodes()]
        graph.node_renderer.data_source.data['course'] = [self.node_to_course_and_wale[node][0] for node in self.node_to_course_and_wale]
        graph.node_renderer.data_source.data['wale'] = [self.node_to_course_and_wale[node][1] for node in self.node_to_course_and_wale]
        graph.node_renderer.data_source.data['bed'] = [self.node_on_front_or_back[node] for node in self.node_on_front_or_back]
        graph.edge_renderer.data_source.data['alpha'] = [0 for edge in G.edges()]
        graph.node_renderer.glyph.update(size=1, fill_color="colors", fill_alpha="alpha") #previously, size = 35; 20; 10(for figure 1). smaller: 5
        graph.edge_renderer.glyph.update(line_alpha="alpha")
        graph.edge_renderer.glyph.line_width = 'scale_width'
        return p


    def visualize(self):
        self.get_nodes_position()
        self.get_nodes_color()
        self.get_yarn_edges()
        self.get_stitch_edges()
        # self.draw_graph() #comment out this line if focusing on UI testing.
        return self.draw_graph_holoviews(), self.knit_graph #for bokeh knit_ui
        # return self.deprecated_draw_graph_holoviews(), self.knit_graph #for panel knit_ui

    